from datetime import datetime, timedelta
import boto3
from boto3.dynamodb.conditions import Key
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
import time
from bs4 import BeautifulSoup
import pandas as pd
import sendgrid
import os
from sendgrid.helpers.mail import *  # noqa: F403
from twilio.rest import Client
import csv 

class Job:
    def __init__(self, name = "", company = "", type = "", salary = "", link = "", loc = "", active = True):
        self.name = name
        self.loc = loc
        self.company = company
        self.type = type
        self.salary = ""
        self.link = link
    
    def __repr__(self):
        s = self.company + "\n" + self.type + "\n" + self.name + "\n"
        s += "\n"
        return s

class JobScraper:
    def __init__(self, url1, url2, type):
        """
        Initialize job list, Selenium Chrome Driver, BeautifulSoup, and DynamoDB objects
        """
        self.url1 = url1
        self.url2 = url2
        self.URL = url1 + str(0) + url2

        # Initialize main objects
        self.jobs = []
        self.mp = {}
        self.links = set()
        self.type = type
        self.count = 0
        self.offset = 0

        options = Options()
        #options.headless = True
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        #self.soup = BeautifulSoup(self.load_and_filter(), "html.parser")
        self.dynamodb = boto3.resource("dynamodb", region_name='us-west-2')
        self.actions = ActionChains(self.driver)

    
    def load_and_filter(self, url, id):
        """
        Go to link, finds all matching groups.
        """
        self.driver.get(url)

        #page_source = self.driver.page_source
        return self.driver.find_elements(By.CLASS_NAME, value=id)

    def filter(self, id):
        return self.driver.find_elements(By.CLASS_NAME, value=id)
    
    def compile(self):
        """
        Scrape jobs
        """
        # Retrieve the table of job listings
        '''
        print(self.count)
        for _ in range(3):
            arrow = self.driver.find_element(By.CLASS_NAME, "MuiButton-root.MuiButton-text.MuiButton-textPrimary.MuiButton-sizeSmall.MuiButton-textSizeSmall.MuiButtonBase-root.css-1f3e5dk")
            self.driver.implicitly_wait(10)
            self.actions.move_to_element(arrow).click().perform()
            self.driver.implicitly_wait(10)
            time.sleep(5)

            #time.sleep(5)
        '''
        
        groups = self.load_and_filter(self.URL, "company-jobs-preview-card_companyOtherJobsTitle__cmhU8")
        self.driver.implicitly_wait(10)
        print(groups)
        curr = groups
        for i in range(len(groups) + 1):
            j = i % len(groups)
        
            self.actions.move_to_element(curr[j]).click().perform()
            time.sleep(1)
            company_element = self.driver.find_element(By.CLASS_NAME, value="company-jobs-preview-card_companyNameAndPromotedContainer__y1dQK")
            self.driver.implicitly_wait(1)

            comp_text = company_element.text
            jobs = self.filter("company-jobs-preview-card_companyJobContainer___zVGi")
            #print(jobs)
            n = len(jobs)
            if i > 0 or self.count >= 1:
                for j in range(n):
                    self.actions.move_to_element(jobs[j]).click().perform()
                    time.sleep(0.5)

                    title_elem = self.driver.find_element(By.CLASS_NAME, "job-details-header_jobTitleRow__mAQC0")
                    self.driver.implicitly_wait(10)
                    title = title_elem.text.split("\n")[0]
                    
                    self.driver.implicitly_wait(10)

                    print(title)
                    try:
                        loc_elem  = self.driver.find_element(By.CLASS_NAME, "job-details-header_detailsRow__uxNNB")
                        self.driver.implicitly_wait(10)
                        arr = loc_elem.text.split("·")
                        if len(arr) == 3:
                            loc = arr[-1]
                        else:
                            loc = arr[-2]
                    except Exception:
                        loc = "view link"
                    #loc = loc_elem.text.split("·")[-2]
                    self.driver.implicitly_wait(10)

                    print(loc)

                    link_elem = self.driver.find_element(By.CLASS_NAME, "job-details-header_applyNowButton__Z_Kd6")
                    self.driver.implicitly_wait(1)

                    time.sleep(0.25)
                    link = link_elem.get_attribute("href")
                    print(link)
                    if link not in self.links:
                        job = Job(name = title, company=comp_text, type=self.type, link=link, loc=loc)
                        self.jobs.append(job)
                        self.links.add(link)
                    #self.mp[company_element.text] = self.mp.get(company_element.text, []) + [job]
                    #self.driver.get(self.URL)
                    #self.driver.refresh()
                    time.sleep(0.25)
                    jobs = self.filter("company-jobs-preview-card_companyJobContainer___zVGi")
                    self.driver.implicitly_wait(5)
                    time.sleep(0.25)
                back = self.driver.find_element(By.CLASS_NAME, "jobs-directory-body_backToCompaniesButton__IakHM")
                self.driver.implicitly_wait(2)
                self.actions.move_to_element(back).click().perform()
                self.driver.implicitly_wait(2)
                #curr = self.filter("company-jobs-preview-card_companyOtherJobsTitle__cmhU8")
                #self.driver.implicitly_wait(5)
            curr = self.filter("company-jobs-preview-card_companyOtherJobsTitle__cmhU8")
            #self.driver.implicitly_wait(5)

            #self.driver.refresh()

            #curr = self.load_and_filter(self.URL, "company-jobs-preview-card_companyOtherJobsTitle__cmhU8")
        with open('tests/test1.csv', 'w', newline='') as csvfile:
            csvfile.truncate()
            writer = csv.writer(csvfile, delimiter=' ',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for job in self.jobs:
                print(job)
                writer.writerow([job.company, job.type, job.name, job.loc, job.link])
        #self.driver.get(self.URL)
        #self.driver.implicitly_wait(10)
        #print(self.URL)
        
        #self.driver.find_element()
        #self.URL = self.driver.current_url
        #print(self.URL)
        '''arrow = self.driver.find_element(By.CLASS_NAME, "MuiButton-root.MuiButton-text.MuiButton-textPrimary.MuiButton-sizeSmall.MuiButton-textSizeSmall.MuiButtonBase-root.css-1f3e5dk")
        self.driver.implicitly_wait(10)
        self.actions.move_to_element(arrow).click().perform()
        time.sleep(5)'''
        self.count += 1
        self.offset += 5
        self.URL = self.url1 + str(self.offset) + self.url2
        self.driver.get(self.URL)
        #self.driver.refresh()
        time.sleep(2)
        self.compile()


        '''
        table = self.soup.find("table", attrs={"class": "hiring-companies-table"})

        # Iterate through each row and grab data except column headers row
        for row in table.find_all("tr")[1:]:
            # Extract valid job listing values, otherwise ignore
            try:
                company = row.find("th").text.strip()
            except:
                continue

            locations, date, url = row.find_all("td")[1:]

            locations = self.parse_locations(locations)

            # Show new job listings in Utah or Remote only
            if not locations:
                continue

            # Parse out date and format to mm/dd/yyyy
            date = self.parse_date(date)

            url = url.find("a")['href']

            job = [company, ', '.join(locations), datetime.strftime(date, "%m/%d/%Y"), url]

            # Only show new job listings and check if it's not in database
            if self.is_new(date) and not self.job_exists(job):
                self.jobs.append(job)

        # Send notifications if there are new jobs available
        if self.jobs:
            print("{} new job(s) available".format(len(self.jobs)))
            self.send_text()
            self.send_email()
        else:
            print("No new jobs available")'''

    def send_email(self):
        """
        Send email to apply to new job(s)
        """

        html = self.display_data(self.jobs).to_html()
        message = Mail(From(os.environ['EMAIL']),
                       To(os.environ['EMAIL']),
                       Subject("Levels.fyi Job Alerts"),
                       PlainTextContent("Your job alert for Software Engineer"),
                       HtmlContent("<h2>Your job alert for software engineer</h2>" + html))
        try:
            sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
            sg.client.mail.send.post(request_body=message.get())
            print("Email sent successfully")
        except Exception as e:
            print(e)
    '''
    def send_text(self):
        """
        Send text alert to notify of new job(s)
        """
        account_sid = os.environ['TWILIO_ACCOUNT_SID']
        auth_token = os.environ['TWILIO_AUTH_TOKEN']
        client = Client(account_sid, auth_token)

        try:
            client.messages \
                .create(body="{} new Software Engineer jobs from Levels.fyi".format(len(self.jobs)),
                        from_=os.environ['TWILIO_NUMBER'],
                        to=os.environ['NUMBER'])
            print("Text sent successfully")
        except Exception as e:
            print(e)

    def is_new(self, date, days_before_today=0):
        """
        Return true if new jobs are available, false otherwise
        :param days_before_today:
        :param date:
        :return:
        """
        today = datetime.combine(datetime.utcnow() - timedelta(days=days_before_today, hours=6), datetime.min.time())
        return date >= today

    def job_exists(self, job):
        """
        Check if job already exists in database
        Return true if exists, otherwise false
        :param job:
        :return:
        """
        table = self.dynamodb.Table('Jobs')

        company, location, date, link = job

        # Grab job to check if it exists
        db_jobs = table.query(
            KeyConditionExpression=Key('company').eq(company)
        )['Items']

        # Add job if it doesn't exist
        if not db_jobs:
            table.put_item(
                Item={
                    'company': company,
                    'location': location,
                    'date': date,
                    'link': link
                }
            )
            return False
        else:
            # Compare date times of existing entries
            dt = datetime.strptime(date, '%m/%d/%Y')
            item = db_jobs[0]
            prev_dt = datetime.strptime(item['date'], '%m/%d/%Y')
            # Update date column to newer date
            if dt > prev_dt:
                item['date'] = date
                table.put_item(Item=item)
            return True


    def parse_locations(self, locations):
        """
        Helper function to parse and return locations: Remote/Utah
        :param locations:
        :return:
        """
        locations = locations.text.strip().split(',')
        new_locations = set()
        for location in set(locations):
            if "Remote" in location:
                new_locations.add("Remote")
            elif "UT" in location:
                new_locations.add("Utah")
        return new_locations

    def parse_date(self, date):
        """
        Helper function to parse and format date to mm/dd/yyyy
        :param date:
        :return:
        """
        date = date .text.strip().split(' ')
        month = datetime.strptime(date[0], '%b').month
        day = int(date[1])
        year = int(date[2]) if len(date) > 2 else datetime.today().year

        return datetime(year=year, month=month, day=day)

    def display_data(self, job_list):
        """
        Helper function to print out data in a formatted table
        :param job_list:
        """
        pd.set_option('display.max_rows', 500)
        pd.set_option('display.max_columns', 500)
        pd.set_option('display.width', 1000)

        df = pd.DataFrame(job_list, columns=["Company", "Location", "Date", "Link"])

        return df
'''

if __name__ == '__main__':
    js = JobScraper('https://www.levels.fyi/jobs/title/product-manager/level/internship?offset=', "&jobId=137270530722931398", "Product Manager")
    js.driver.get(js.URL)
    js.compile()