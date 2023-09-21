from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
from chromedriver_py import binary_path
from bs4 import BeautifulSoup

# Define the path to the Chrome WebDriver executable
svc = webdriver.ChromeService(executable_path=binary_path)
driver = webdriver.Chrome(service=svc)
driver.set_window_size(1000, 1000)


# Define a function for extracting text from a BeautifulSoup object
def extract_text(soup, element_selector, class_name):
    element = soup.find(element_selector, class_=class_name)
    return element.text.strip() if element else ""


# Close glassdoor popup asking you to signin/signup
def close_popup(job_container):
    try:
        wait = WebDriverWait(driver, 1)
        element = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="LoginModal"]/div/div/div/div[2]/button')
            )
        )
        if element:
            element.click()
    except TimeoutException:
        pass

    job_container.click()

    try:
        wait = WebDriverWait(driver, 1)
        element = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="LoginModal"]/div/div/div/div[2]/button')
            )
        )
        if element:
            element.click()
    except TimeoutException:
        pass


def get_jobs(url, output_file):
    jobs_list = []
    page_num = 0

    try:
        driver.get(url)

        # find total number of jobs available. Will loop till completed this.
        time.sleep(3)
        max_jobs_cont = driver.find_element(
            By.XPATH, '//*[@id="MainCol"]/div[1]/div[1]/div/div/h1'
        )
        max_jobs = BeautifulSoup(max_jobs_cont.get_attribute("outerHTML"), "lxml").text
        num_jobs = int(max_jobs[: max_jobs.find(" ")])

        while len(jobs_list) < num_jobs:
            # click on the next page button once we finish the job listings on current page
            if len(jobs_list) >= 10:
                try:
                    driver.find_element(
                        By.XPATH, '//*[@id="MainCol"]/div[2]/div/div[1]/button[7]'
                    ).click()
                    page_num += 1
                except NoSuchElementException:
                    break
            current_url = driver.current_url

            time.sleep(5)
            # locate the conatainers with job postings
            job_listings = driver.find_elements(By.CLASS_NAME, "react-job-listing")
            # loop through the list of job posting containers

            for job in job_listings:
                if len(jobs_list) >= num_jobs:
                    break

                close_popup(job)

                # finding and loading in all the elements and html. With these we can narrow down on text we need using beautiful soup
                job_overall = BeautifulSoup(job.get_attribute("outerHTML"), "lxml")
                job_over_loc = driver.find_element(By.ID, "JDCol")
                job_overview = BeautifulSoup(
                    job_over_loc.get_attribute("outerHTML"), "lxml"
                )
                job_description_div = job_overview.find(
                    "div", class_="jobDescriptionContent desc"
                )
                company_info_div = job_overview.find("div", class_="d-flex flex-wrap")

                # Defining all variables we want in our df by searching through html code from above and extracting text
                extracted_text = []
                if job_description_div:
                    for element in job_description_div.find_all(["p", "li"]):
                        extracted_text.append(element.text.strip())

                company = ""

                if page_num == 0:
                    company = extract_text(job_overall, "div", "job-search-8wag7x")
                else:
                    company = extract_text(job_overall, "div", "css-8wag7x")

                title = extract_text(job_overall, "div", "job-title mt-xsm")
                location = extract_text(job_overall, "div", "location mt-xxsm")
                salary = extract_text(job_overall, "div", "salary-estimate")
                rating = extract_text(job_overview, "div", "mr-sm css-ey2fjr e1pr2f4f2")
                description = "\n".join(extracted_text)
                size = ""
                revenue = ""
                industry = ""
                sector = ""

                # the company info table seems to have the same class
                # Might be a more efficient way but I was able to use the label text to help me differentiate
                if company_info_div:
                    for table_cell in company_info_div.find_all(
                        "div",
                        class_="d-flex justify-content-start css-rmzuhb e1pvx6aw0",
                    ):
                        label = table_cell.find(
                            "span", class_="css-1taruhi e1pvx6aw1"
                        ).text.strip()
                        value = table_cell.find(
                            "span", class_="css-i9gxme e1pvx6aw2"
                        ).text.strip()

                        if "Size" in label:
                            size = value
                        elif "Revenue" in label:
                            revenue = value
                        elif "Industry" in label:
                            industry = value
                        elif "Sector" in label:
                            sector = value

                # append the job listing to our list of jobs
                jobs_list.append(
                    {
                        "Company": company,
                        "Title": title,
                        "Location": location,
                        "Salary": salary,
                        "Industry": industry,
                        "Revenue": revenue,
                        "Size": size,
                        "Description": description,
                        "Rating": rating,
                        "Sector": sector,
                    }
                )

    # Had to google this but i added this so that no matter what everything that has been scraped is saved
    # Sometimes the ip gets blocked or a captcha shows up and breaks the scraper. Now it'll save everything before quitting
    except Exception as e:
        print(f"An error occurred str{e}")
    finally:
        print(
            f"{len(jobs_list)} Scraped Successfully There were {num_jobs}. {current_url}"
        )
        df = pd.DataFrame(jobs_list)
        df.to_excel(f"Data\\{output_file}.xlsx", index=False)


# Call the function to start scraping.
# Insert Glassdoor URL here
get_jobs(
    "https://www.glassdoor.com/Job/united-states-data-analyst-jobs-SRCH_IL.0,13_IN1_KO14,26.htm",
    "glassdoor_raw_usa",
)
