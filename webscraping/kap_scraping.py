from pymongo import MongoClient
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import requests
from translation import process_excel_html
from llm import convertToMD, md_to_text
from upload import saveFileToKG

def create_notification_index(firm_name, notification_ids_array):
    # Connect to MongoDB
    client = MongoClient("mongodb+srv://hakanm:1234@bitirme.eksxx.mongodb.net/?retryWrites=true&w=majority&appName=bitirme")
    db = client["chatbot_db"]
    collection = db["kap_notification_indexes"]

    # Check if an object with the same firm_name already exists
    existing_document = collection.find_one({"firm_name": firm_name})

    if existing_document is None:
        # If no document exists with the same firm_name, insert a new one
        new_document = {
            "firm_name": firm_name,
            "notification_ids_array": notification_ids_array
        }
        collection.insert_one(new_document)
        print(f"Created new entry for {firm_name}.")
    else:
        # If the firm_name exists, don't insert anything
        print(f"Entry for {firm_name} already exists. No new entry created.")

def check_notification_id(firm_name, notification_id):
    # Connect to MongoDB
    client = MongoClient("mongodb+srv://hakanm:1234@bitirme.eksxx.mongodb.net/?retryWrites=true&w=majority&appName=bitirme")
    db = client["chatbot_db"]
    collection = db["kap_notification_indexes"]

    # Find the document with the given firm_name
    document = collection.find_one({"firm_name": firm_name})

    if document:
        # Check if the notification_id is in the notification_ids_array
        if notification_id in document["notification_ids_array"]:
            return True
        else:
            return False
    else:
        # If no document found with the given firm_name
        print(f"No entry found for {firm_name}.")
        return False

def add_notification_id(firm_name, notification_id):
    # Connect to MongoDB
    client = MongoClient("mongodb+srv://hakanm:1234@bitirme.eksxx.mongodb.net/?retryWrites=true&w=majority&appName=bitirme")
    db = client["chatbot_db"]
    collection = db["kap_notification_indexes"]

    # Find the document with the given firm_name
    document = collection.find_one({"firm_name": firm_name})

    if document:
        # Check if the notification_id already exists in the array to avoid duplicates
        if notification_id not in document["notification_ids_array"]:
            # Add the notification_id to the array
            collection.update_one(
                {"firm_name": firm_name},
                {"$push": {"notification_ids_array": notification_id}}
            )
            print(f"Notification ID {notification_id} added to {firm_name}'s array.")
        else:
            print(f"Notification ID {notification_id} already exists in {firm_name}'s array.")
    else:
        # If no document found with the given firm_name
        print(f"No entry found for {firm_name}.")


def downloadAndSaveToTemp(kap_no):
    download_url = "https://www.kap.org.tr/en/api/notification/export/excel/" + str(kap_no)
    response = requests.get(download_url)

    # Check if the request was successful
    if response.status_code == 200:
        # Specify the full path where you want to save the file 
        file_path = f"/Users/hakanmuluk/Desktop/webscraping/temp/notification_{kap_no}.xlsx" 
        with open(file_path, "wb") as f:
            f.write(response.content)
        print("File downloaded and saved at:", file_path)
        return file_path
    else:
        print("Failed to download file. Status code:", response.status_code)
        return None

def checkNewNotificationAndTranslate(firmName):
    create_notification_index(firmName, [])
    driver = webdriver.Chrome()  # Ensure ChromeDriver is installed and in PATH
    driver.get("https://www.kap.org.tr/en/bildirim-sorgu")

    wait = WebDriverWait(driver, 10)

    # Open the Companies menu
    companies_menu = wait.until(EC.element_to_be_clickable((By.ID, "custom-select-1")))
    companies_menu.click()
    time.sleep(1)  # Brief pause for the menu to open

    # Locate and click the label for "KOÇ HOLDİNG A.Ş."
    firm_label = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, f"//label[contains(@class, 'cursor-pointer') and contains(., '{firmName}')]") #KOÇ HOLDİNG A.Ş.
        )
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", firm_label)
    time.sleep(1)
    try:
        firm_label.click()
    except Exception as e:
        print("Standard click failed; attempting JavaScript click on the label:", e)
        try:
            driver.execute_script("arguments[0].click();", firm_label)
        except Exception as e2:
            print("JavaScript click on label failed; attempting to hide header and retry:", e2)
            driver.execute_script(
                "document.querySelectorAll('.header__nav--menu').forEach(function(el) { el.style.display='none'; });"
            )
            time.sleep(1)
            driver.execute_script("arguments[0].click();", firm_label)

    # Close or reset the companies menu
    companies_menu_again = wait.until(EC.element_to_be_clickable((By.ID, "custom-select-1")))
    companies_menu_again.click()
    time.sleep(5)

    # ------------------------------
    # STEP 2: Set Date Interval to "Last 1 Week" and click Search
    # ------------------------------

    # Open the Date Interval dropdown (toggle that shows "Today")
    date_interval_toggle = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//div[contains(@class, 'custom-select-toggle') and .//span[normalize-space()='Today']]")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", date_interval_toggle)
    time.sleep(1)
    try:
        date_interval_toggle.click()
    except Exception as e:
        print("Standard click failed on Date Interval toggle; using JavaScript click. Error:", e)
        driver.execute_script("arguments[0].click();", date_interval_toggle)
        time.sleep(1)

    # Allow dropdown to fully open
    time.sleep(5)

    # Click "Last 1 Week" option
    last_week_option = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//div[contains(@class, 'select-option') and normalize-space()='Last 1 Month']") # do it Week
        )
    )
    last_week_option.click()
    time.sleep(3)

    # Click the "Search" button
    search_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[normalize-space()='Search' and contains(@class, 'bg-light-dark')]")
        )
    )
    search_button.click()
    time.sleep(3)

    # ------------------------------
    # STEP 3: Iterate over notifications to open each detail page and print its URL
    # ------------------------------

    main_window = driver.current_window_handle
    url_date_array = []
    i = 0

    while True:
        # Refresh list of notification rows (<tr> elements whose id starts with "notification")
        notifications = driver.find_elements(By.XPATH, "//tr[starts-with(@id, 'notification')]")
        
        # If no more notifications or we've processed all, break out of loop
        if i >= len(notifications):
            print("No more notifications found.")
            break
        
        notification = notifications[i]
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", notification)
        time.sleep(1)
        
        try:
            notification.click()
        except Exception as click_error:
            print(f"Failed to click notification at index {i}. Error: {click_error}")
            i += 1
            continue

        # Wait for new tab/window to open
        WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
        
        # Switch to the new tab
        for handle in driver.window_handles:
            if handle != main_window:
                driver.switch_to.window(handle)
                break
                
        time.sleep(2)  # Allow page to load
        url = driver.current_url
        print("Notification URL:", url)

        try:
            # This XPath locates the first <span> after the "Publish Date" label,
            # which contains the date text such as "09.04.2025".
            publish_date_element = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//div[contains(text(), 'Publish Date')]/following-sibling::div[1]/span[1]")
                )
            )
            publish_date = publish_date_element.text
            print("Publish Date:", publish_date)
        except Exception as e:
            print("Error extracting publish date:", e)

        #clicked_urls.append(url)
        
        match = re.search(r'/(\d+)$', url)
        if match:
            number_part = match.group(1)
            isAdded = check_notification_id(firmName, int(number_part))
            print("********")
            print(isAdded)
            print("********")
            if isAdded:
                driver.close()
                driver.switch_to.window(main_window)
                break
        
        pair = url, publish_date
        url_date_array.append(pair)
        add_notification_id(firmName, int(number_part))
        driver.close()
        driver.switch_to.window(main_window)
        time.sleep(1)
        i += 1
    print(url_date_array)
    #clicked_urls.pop()
    print("********************")
    print(url_date_array)
    print("All clicked Notification URLs:")
    for obj in url_date_array:
        link = obj[0]
        match = re.search(r'/(\d+)$', link)
        if match:
            number_part = match.group(1)
            downloaded_path = downloadAndSaveToTemp(number_part)
            """ if downloaded_path:
                translated_path = f"/Users/hakanmuluk/Desktop/webscraping/temp_translated/notification_{number_part}.html"
                process_excel_html(downloaded_path, translated_path) """
            if downloaded_path:
                with open(downloaded_path, "r", encoding="utf-8") as file:
                    html_content = file.read()
                md_version = convertToMD(html_content)
                text_version = md_to_text(md_version)
                saveFileToKG(firmName, text_version, obj[1])


            print("Extracted number using regex:", number_part)
            time.sleep(75)
        else:
            print("No number found at the end of the URL.")

checkNewNotificationAndTranslate("TÜRK HAVA YOLLARI A.O.")


