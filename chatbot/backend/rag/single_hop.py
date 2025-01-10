# single_hop.py

from typing import Optional, Callable
from typing_extensions import TypedDict
from langgraph.graph import StateGraph  # We still use your StateGraph type
from concurrent.futures import ThreadPoolExecutor
from neo4j import GraphDatabase
from .prompts import (
    rephrase_For_Followup,
    translateEnglish,
    translateTurkish,
    relevancy_Check,
    generate_answer,
    checkSupported,
    decomposeToSubqueries
)
from .retrieval import (
    retrieveForSingleHop,
    retrieveForSingleHopWithoutFilter
)

uri = "bolt://localhost:7687"
username = "neo4j"
password = "strongpassword"
driver = GraphDatabase.driver(uri, auth=(username, password))

class GraphState(TypedDict):
    userQuery: str
    rephrasedUserQuery: str
    englishUserQuery: str
    retrievedDocs: list[str]
    relevantDocs: list[str]
    pastMessages: str
    answerGenerated: str
    isAnswerSupported: bool
    turkishAnswer: str
    isDecomposed: bool
    decomposedQueries: list[str]
    answerNotFound: bool
    comeFrom: str  # "relCheck" or "supCheck"
    finalAnswer: str
    # We'll skip visited_nodes here since we'll handle steps externally

# ---------------- Node Functions (unchanged) ----------------

def rephraseForFollowup(state: GraphState) -> GraphState:
    if len(state["pastMessages"]) > 0:
        state["rephrasedUserQuery"] = rephrase_For_Followup(
            state["userQuery"], state["pastMessages"]
        )
    else:
        state["rephrasedUserQuery"] = state["userQuery"]
    return state

def translateToEnglish(state: GraphState) -> GraphState:
    state["englishUserQuery"] = translateEnglish(state["rephrasedUserQuery"])
    return state

def retrieval(state: GraphState) -> GraphState:
    if not state["isDecomposed"]:
      
        docs = retrieveForSingleHop(state["englishUserQuery"], driver)
      
        if len(docs) == 0:
            docs = retrieveForSingleHopWithoutFilter(state["englishUserQuery"], driver)
        state["retrievedDocs"] = docs
    else:
        # If the question was decomposed
        retrievedDocs = []
        for query in state["decomposedQueries"]:
            retrievedDocs = retrieveForSingleHop(query, driver)
            for doc in retrievedDocs:
                if doc not in state["retrievedDocs"]:
                    state["retrievedDocs"].append(doc)
    return state

def relevancyCheck(state: GraphState) -> GraphState:
    docs = state["retrievedDocs"]
    query = state["englishUserQuery"]
    valid_docs = []
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(relevancy_Check, doc, query): doc for doc in docs}
        for future in futures:
            doc = futures[future]
            try:
                if future.result():
                    valid_docs.append(doc)
            except Exception as e:
                print(f"Error processing {doc}: {e}")
    state["relevantDocs"] = valid_docs
    state["comeFrom"] = "relCheck"
    return state

def generateAnswer(state: GraphState) -> GraphState:
    ans = generate_answer(state["relevantDocs"], state["englishUserQuery"])
    state["answerGenerated"] = ans
    return state

def supportednessCheck(state: GraphState) -> GraphState:
    isSupported = checkSupported(
        state["relevantDocs"], state["englishUserQuery"], state["answerGenerated"]
    )
    state["isAnswerSupported"] = isSupported
    if not isSupported:
        new_ans = generate_answer(state["relevantDocs"], state["englishUserQuery"])
        state["answerGenerated"] = new_ans
        state["isAnswerSupported"] = checkSupported(
            state["relevantDocs"], state["englishUserQuery"], new_ans
        )
    state["comeFrom"] = "supCheck"
    return state

def translateToTurkish(state: GraphState) -> GraphState:
    state["turkishAnswer"] = translateTurkish(state["answerGenerated"])
    return state

def decompose(state: GraphState) -> GraphState:
    subs = decomposeToSubqueries(state["englishUserQuery"])
    state["decomposedQueries"] = subs
    state["isDecomposed"] = True
    return state

def router(state: GraphState) -> str:
    """
    Decide the next node name conditionally (same logic you used in add_conditional_edges).
    """
    if state["isDecomposed"] and (len(state["relevantDocs"]) == 0 and state["comeFrom"] == "relCheck"):
        state["answerNotFound"] = True
        return "end"
    elif state["isDecomposed"] and not state["isAnswerSupported"] and state["comeFrom"] == "supCheck":
        state["answerNotFound"] = True
        return "end"
    elif len(state["relevantDocs"]) == 0 and state["comeFrom"] == "relCheck":
        return "decompose"
    elif not state["isAnswerSupported"] and state["comeFrom"] == "supCheck":
        return "decompose"
    elif state["comeFrom"] == "relCheck":
        return "generateAnswer"
    else:
        return "translateToTurkish"

def end(state: GraphState) -> GraphState:
    if state["answerNotFound"]:
        state["finalAnswer"] = "Bilmiyorum."
    else:
        state["finalAnswer"] = state["turkishAnswer"]
    return state

# ---------------- Adjacency / Step-by-Step Runner ----------------

ADJACENCY = {
    "rephraseForFollowup": ["translateToEnglish"],
    "translateToEnglish": ["retrieval"],
    "retrieval": ["relevancyCheck"],
    "relevancyCheck": router,  # Means "call router(state)" -> next node name
    "generateAnswer": ["supportednessCheck"],
    "supportednessCheck": router,
    "translateToTurkish": ["end"],
    "decompose": ["retrieval"],
    "end": []
}

NODE_FUNCTIONS = {
    "rephraseForFollowup": rephraseForFollowup,
    "translateToEnglish": translateToEnglish,
    "retrieval": retrieval,
    "relevancyCheck": relevancyCheck,
    "generateAnswer": generateAnswer,
    "supportednessCheck": supportednessCheck,
    "translateToTurkish": translateToTurkish,
    "decompose": decompose,
    "end": end
}

ENTRY_POINT = "rephraseForFollowup"
FINISH_NODE = "end"

def get_next_nodes(current_node: str, state: GraphState) -> list[str]:
    """
    If adjacency is a list, return it directly.
    If adjacency is the 'router' function, call it to get the next node name in a list.
    """
    next_info = ADJACENCY[current_node]
    if isinstance(next_info, list):
        return next_info
    else:
        # It's the router function
        next_node_name = next_info(state)
        return [next_node_name]

async def run_pipeline_step_by_step(state: GraphState):
    """
    An async generator that yields (node_name, state) after each node's execution,
    letting us update the Chainlit UI in real time.
    """
    current_node = ENTRY_POINT
    while True:
        # 1) Run the node function
        func = NODE_FUNCTIONS[current_node]
        state = func(state)

        # 2) Yield so Chainlit can show this step
        yield current_node, state

        # 3) If we're at the finish node, break
        if current_node == FINISH_NODE:
            break

        # 4) Otherwise, figure out next node(s)
        next_nodes = get_next_nodes(current_node, state)
        # Usually only 1 next node, unless you do something special
        current_node = next_nodes[0]
