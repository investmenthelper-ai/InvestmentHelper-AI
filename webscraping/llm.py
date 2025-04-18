from openai import OpenAI
from datetime import datetime
from neo4j import GraphDatabase
client = OpenAI(api_key='')

def process_chunk(chunk, current_date, company_name, notificationDate):
    """
    Calls the LLM with the provided prompts and text chunk.

    Args:
        client (OpenAI): OpenAI client instance.
        system_prompt (str): System prompt for the LLM.
        user_prompt (str): User prompt to use with the LLM.
        chunk (str): Text chunk to process.

    Returns:
        str: Response content from the LLM.
    """

    system_prompt = """
    You are a financial information extraction expert that extracts meaningful relationships in the form of (subject-predicate-object-related companies array- date ) for knowledge graph construction. 
    Each fivelet should be descriptive enough so that any one who reads the fivelet should be able to understand the all context. So, specify all the related details into fivelets.
    """

    user_prompt = """
    You are an expert language model specializing in financial text analysis. Your task is to extract "fivelets" from a given text. Each fivelet is a structured representation of information consisting of the following components:
    Entity1: The first entity involved in the relationship.
    Relation: A descriptive action or state capturing a meaningful relationship, avoiding verbs such as "is," "are," "were," or "so."
    Entity2: The second entity involved in the relationship.
    Related Companies: An array of companies related to that specific fivelet (not all companies listed in the text).
    Date Interval: A list containing the start date and end date relevant to the fivelet, formatted as ["Start Date", "End Date"]. If the start or end date is unknown, use "-" in its place.
    Guidelines:
    Descriptive Predicates: Use verbs that convey meaningful actions or states. For example, instead of "X is an engineer," write "X's job is engineering."
    Avoid Comma-Separated Values: Do not include multiple entities or relationships within a single fivelet. If multiple entities or relationships are present, create separate fivelets.
    Include All Relevant Details: Ensure each fivelet is detailed and encompasses all pertinent subjects and specifics.
    Related Companies Array: Always list the companies related to that specific fivelet in the array.
    Extract All Possible Fivelets: Thoroughly extract as many fivelets as possible from the text.
    Date Intervals: Use date intervals to represent the time frame of each fivelet. Be as specific as possible with dates. If only one date is known, place it appropriately and use "-" for the unknown date.
    Self-Contained Fivelets: Each fivelet must be meaningful and understandable on its own without relying on other fivelets for context. Avoid vague references; provide sufficient detail within each fivelet to make it independently clear.
    Process:
    Think Step by Step: Identify all entities, relationships, and relevant dates in the text before extracting fivelets.
    Planning: Outline the key points and events along with their associated dates.
    Extraction: Use your plan to extract fivelets, ensuring each one adheres to the specified format and is self-contained.
    Additional Guidelines:
    Date Intervals: Represent dates as intervals ["Start Date", "End Date"]. Use specific dates when available; otherwise, use "-" to indicate an unknown start or end date.
    Precision in Dates: Be as precise as possible with dates (day, month, year).
    Start and End Dates: The start date signifies when the event or relationship began, and the end date signifies when it ended or was reported.
    Avoid Generic Dates: Do not use broad dates like just the year unless that is all the information provided.
    Include All Information: Ensure all relevant fivelets from the text are extracted, formatted correctly, and are self-contained.
    Examples:
    Text:
    YEOTK's notification on 15.09.2024:
    On 13.08.2024, we announced the partnership agreement we signed with Shanghai Electric Power Co Ltd (SEP) to jointly carry out two separate solar power plant investments under the subsidiaries of DEFIC Globe Enerji A.Ş. (Defic Globe), in which our company holds a 51% stake, in Romania.
    Under the agreement, the investment in the plants with a total capacity of 129 MWp, located in our subsidiaries in Romania, will be made in collaboration with Shanghai Electric Power Co Ltd (SEP), one of China's leading energy groups with an installed capacity of 22,400 MWh as of the end of 2023.
    The turnkey construction of the solar power plants, including engineering services, high voltage transformer substations, and the installation of energy transmission lines, will also be undertaken by our group, and a contract worth EUR 65.8 million has been signed.
    Fivelets:
    ("YEOTK", "announced partnership agreement with", "Shanghai Electric Power Co Ltd (SEP) for joint investments", ["YEOTK", "SEP"], ["13.08.2024", "13.08.2024"])
    ("YEOTK and SEP", "signed partnership agreement", "on 13.08.2024", ["YEOTK", "SEP"], ["13.08.2024", "13.08.2024"])
    ("YEOTK and SEP", "will jointly invest in", "two separate solar power plants in Romania", ["YEOTK", "SEP"], ["13.08.2024", "-"])
    ("DEFIC Globe Enerji A.Ş. (Defic Globe)", "is a subsidiary where YEOTK holds 51% stake", "used for investments", ["YEOTK", "Defic Globe"], ["-", "15.09.2024"])
    ("Investments by YEOTK and SEP", "are under subsidiaries of", "DEFIC Globe Enerji A.Ş. (Defic Globe)", ["YEOTK", "SEP", "Defic Globe"], ["13.08.2024", "-"])
    ("Total capacity of the solar power plants", "is", "129 MWp", ["YEOTK", "SEP"], ["13.08.2024", "-"])
    ("Shanghai Electric Power Co Ltd (SEP)", "is one of China's leading energy groups", "with installed capacity of 22,400 MWh as of end 2023", ["SEP"], ["-", "31.12.2023"])
    ("YEOTK's group", "will undertake", "turnkey construction including engineering services", ["YEOTK"], ["13.08.2024", "-"])
    ("Turnkey construction by YEOTK", "includes", "high voltage transformer substations", ["YEOTK"], ["13.08.2024", "-"])
    ("Turnkey construction by YEOTK", "includes", "installation of energy transmission lines", ["YEOTK"], ["13.08.2024", "-"])
    ("Contract for construction signed by YEOTK and SEP", "is worth", "EUR 65.8 million", ["YEOTK", "SEP"], ["-", "-"])
    ("YEOTK's investments", "are located in", "Romania", ["YEOTK"], ["13.08.2024", "-"])
    ("YEOTK", "announced the partnership agreement", "on 15.09.2024", ["YEOTK"], ["15.09.2024", "15.09.2024"])
    Text:
    KOÇ Holding's notification on 05.11.2024:
    It has been decided by the board of directors of Enerji Yatırımları A.Ş. (EYAŞ), in which our company holds a 77% stake and our subsidiary Aygaz A.Ş. holds a 20% stake, to distribute a cash advance dividend of 7,620,000,000 TL to be paid from EYAŞ's profit for the first nine months of 2024, and to be paid by 31.10.2024.
    The English translation of this announcement is attached. In case of any discrepancies between the versions, the Turkish version shall prevail.
    Fivelets:
    ("KOÇ Holding", "holds 77% stake in", "Enerji Yatırımları A.Ş. (EYAŞ)", ["KOÇ Holding", "EYAŞ"], ["-", "05.11.2024"])
    ("Aygaz A.Ş.", "is a subsidiary of", "KOÇ Holding", ["Aygaz A.Ş.", "KOÇ Holding"], ["-", "05.11.2024"])
    ("Aygaz A.Ş.", "holds 20% stake in", "Enerji Yatırımları A.Ş. (EYAŞ)", ["Aygaz A.Ş.", "EYAŞ"], ["-", "05.11.2024"])
    ("Board of directors of EYAŞ", "decided to distribute", "cash advance dividend of 7,620,000,000 TL", ["EYAŞ"], ["05.11.2024", "05.11.2024"])
    ("Dividend payment from EYAŞ", "will be paid from", "profit for first nine months of 2024", ["EYAŞ"], ["01.01.2024", "30.09.2024"])
    ("Deadline for dividend payment by EYAŞ", "is", "31.10.2024", ["EYAŞ"], ["-", "31.10.2024"])
    ("KOÇ Holding's announcement", "includes", "English translation attached", ["KOÇ Holding"], ["05.11.2024", "05.11.2024"])
    ("Turkish version of the announcement", "prevails over", "English version in case of discrepancies", ["KOÇ Holding"], ["05.11.2024", "05.11.2024"])
    ("EYAŞ", "decided to distribute dividend", "on 05.11.2024", ["EYAŞ"], ["05.11.2024", "05.11.2024"])
    ("Dividend from EYAŞ", "to be paid", "by 31.10.2024", ["EYAŞ"], ["-", "31.10.2024"])
    Text:
    ETYAK's notification on 16.11.2024:
    In accordance with the provision of Article 36, paragraph 2 of the Capital Markets Board's (III-48.5) Communiqué on the Principles Regarding Securities Investment Trusts, titled "Disclosure and Public Information," which states: "In cases where the weighted average price of the partnership's shares on BİAŞ exceeds twice the net asset value per share, it is mandatory to publish the sector-based portfolio and net asset value table on the Public Disclosure Platform (KAP) every business day, starting from the following business day until this situation no longer exists." Accordingly, the sector-based portfolio and total value table dated 17.10.2024 are presented for the information of our shareholders, investors, and the public.
    Fivelets:
    ("ETYAK", "complies with", "Article 36, paragraph 2 of Capital Markets Board's Communiqué", ["ETYAK", "Capital Markets Board"], ["16.11.2024", "16.11.2024"])
    ("Article 36, paragraph 2", "requires", "publication of sector-based portfolio when share price exceeds threshold", ["Capital Markets Board"], ["-", "16.11.2024"])
    ("ETYAK's share price", "exceeded", "twice the net asset value per share", ["ETYAK"], ["-", "16.11.2024"])
    ("ETYAK", "published", "sector-based portfolio dated 17.10.2024", ["ETYAK"], ["17.10.2024", "17.10.2024"])
    ("ETYAK", "published", "net asset value table dated 17.10.2024", ["ETYAK"], ["17.10.2024", "17.10.2024"])
    ("Sector-based portfolio and net asset value table", "are presented for", "shareholders", ["ETYAK"], ["17.10.2024", "-"])
    ("Sector-based portfolio and net asset value table", "are presented for", "investors", ["ETYAK"], ["17.10.2024", "-"])
    ("Sector-based portfolio and net asset value table", "are presented for", "the public", ["ETYAK"], ["17.10.2024", "-"])
    ("Requirement to publish daily", "starts from", "the following business day after share price exceeds threshold", ["Capital Markets Board"], ["-", "16.11.2024"])
    ("Publication requirement", "continues until", "the situation no longer exists", ["Capital Markets Board"], ["-", "16.11.2024"])
    ("Article 36, paragraph 2", "is part of", "Communiqué on the Principles Regarding Securities Investment Trusts", ["Capital Markets Board"], ["-", "16.11.2024"])
    ("Communiqué III-48.5", "is titled", "Disclosure and Public Information", ["Capital Markets Board"], ["-", "16.11.2024"])
    Text:
    Tat's notification on 30.09.2024:
    In relation to the investment decision in the sauces and ready-made meals categories, with an investment cost of approximately 10 million Euros, as announced in our special circumstance disclosures dated 18.04.2024, for the additional capacity increase plan of 40 million units/year in the sauces category; our current production capacity of plastic bottle sauces (ketchup/mayonnaise and other seasoning sauces), which was 70 million units/year, has been increased by 10 million units/year, reaching a total capacity of 85 million units/year. The cost of the investment expenditures made for machinery equipment, construction, infrastructure, and storage areas amounts to 2.6 million Euros. Also, we have signed an agreement with KOÇ Holding and Sabancı and got their investments.
    Fivelets:
    ("Tat", "announced investment decision in", "sauces and ready-made meals categories costing approximately 10 million Euros", ["Tat"], ["18.04.2024", "18.04.2024"])
    ("Tat", "plans additional capacity increase of", "40 million units/year in sauces category", ["Tat"], ["18.04.2024", "-"])
    ("Tat's production capacity of plastic bottle sauces", "was", "70 million units/year before increase", ["Tat"], ["-", "30.09.2024"])
    ("Tat", "increased production capacity by", "10 million units/year", ["Tat"], ["30.09.2024", "30.09.2024"])
    ("Tat's total production capacity", "reached", "85 million units/year", ["Tat"], ["30.09.2024", "-"])
    ("Investment expenditures by Tat", "amount to", "2.6 million Euros for machinery, construction, infrastructure, and storage", ["Tat"], ["30.09.2024", "30.09.2024"])
    ("Tat", "signed agreement with", "KOÇ Holding for investment", ["Tat", "KOÇ Holding"], ["-", "30.09.2024"])
    ("Tat", "signed agreement with", "Sabancı for investment", ["Tat", "Sabancı"], ["-", "30.09.2024"])
    ("Tat", "received investments from", "KOÇ Holding and Sabancı", ["Tat", "KOÇ Holding", "Sabancı"], ["-", "30.09.2024"])
    ("Tat's capacity increase", "includes", "plastic bottle sauces like ketchup, mayonnaise, and other seasoning sauces", ["Tat"], ["30.09.2024", "-"])
    ("Special circumstance disclosures by Tat", "were dated", "18.04.2024", ["Tat"], ["18.04.2024", "18.04.2024"])
    Please use these guidelines and examples to extract fivelets from any given text, ensuring clarity, accuracy, completeness, and that each fivelet is self-contained and meaningful on its own.

    Text:
    """
    user_prompt += f"{company_name}'s Notification on {notificationDate}, todays date is: {current_date}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt + "\n\n" + chunk}
        ],
        temperature=0.12
    )
    return response.choices[0].message.content

def convertToMD(html_text):
    user_prompt = f"""Convert this to markdown format by also preserving the tables please. Dont miss any detail:
    {html_text}
    Please do not write any other thing, only write the markdown."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.12,
        max_tokens=6000,
    )
    return response.choices[0].message.content

def md_to_text(md_text):
    system_prompt = """You are a language model tasked with transforming Markdown content into a cohesive narrative text. 
    The input will include various elements such as textual information, financial tables, and other structured details. 
    Your output must integrate every piece of information without omitting any details. Write the output in continuous, 
    coherent paragraphs instead of lists or bullet-pointed items. Do not mention or refer to the original Markdown format or structure in your output. 
    In addition, when you encounter financial numbers presented in a shorthand format (i.e., a number that conventionally represents 1000 TL), 
    convert these values to their full numerical form by multiplying them by 1000 TL. Accuracy and completeness are paramount."""

    user_prompt = f"""Please convert the following Markdown file into a well-structured narrative. 
    The output should be written as uninterrupted paragraphs that seamlessly incorporate all the text, financial data, 
    and detailed content included in the Markdown file. Do not use lists or item-by-item formats, 
    and avoid mentioning that the information originally came from a Markdown document. Additionally, 
    if any financial values appear as shorthand (where a number stands for 1000 TL), convert those into the exact full amounts by multiplying by 1000 TL. 
    Ensure that every detail is retained and correctly transformed in your narrative output.

    Markdown:
    {md_text}
    
    Again, your output should be understood as if it was the original one, do not do references to the file I gave. 
    Lastly, while giving the numbers, use the conventions(like if it is said that a number represents dollars, use dollar sign or a number represents 10 dollars,
    give those numbers by multiplying with 10. The numbers you give are critical, they must be true!"""

    response = client.chat.completions.create(model="o3-mini", 
        messages= [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        reasoning_effort="medium", store=False, timeout=60)
    
    return response.choices[0].message.content


s = """In addressing income-related issues, the company stated that neither it nor its shareholders, partners, or subsidiaries derive any income or engage in operations such as the production or trade of alcoholic beverages or foods, pork products, tobacco products for smoking, gambling or gambling-like activities, or any financial sector operations outside of participation finance. Also, Banvit has done a deal with KOC HOLDİNG in 01.02.2025. Additionally, there are no publishing activities, nor are there any earnings from hotel management, tourism, entertainment, or organizational activities that contradict Islamic values. Furthermore, income derived from noncompliant activities that is permitted up to 5% under Guideline Article 3.2 was reported as nil, with no revenue generated from retail sales of harmful tobacco products, from business or services to companies not operating under participation finance principles, from rental activities involving such companies, or from advertising, branding, sponsorship, or brokerage activities, resulting in a total of 0 TL."""

#k = process_chunk(s, "12.04.2025", "BANVİT", "05.03.2025")

#print(k)