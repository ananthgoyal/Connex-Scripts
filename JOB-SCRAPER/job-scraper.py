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

class Job:
    def __init__(self, name = "", company = "", type = "", salary = "", active = True):
        self.name = ""
        self.company = ""
        self.type = ""
        self.salary = ""
        self.link = ""
        self.active = active


class JobScraper:
    def __init__(self):
        """
        Initialize job list, Selenium Chrome Driver, BeautifulSoup, and DynamoDB objects
        """
        self.URL = 'https://www.levels.fyi/jobs/title/product-manager/level/internship?jobId=137270530722931398'

        # Initialize main objects
        self.jobs = []

        options = Options()
        #options.headless = True
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        #self.soup = BeautifulSoup(self.load_and_filter(), "html.parser")
        self.dynamodb = boto3.resource("dynamodb", region_name='us-west-2')
        self.actions = ActionChains(self.driver)

    
    def load_and_filter(self):
        """
        Go to link, finds all matching groups.
        """
        self.driver.get(self.URL)
        #page_source = self.driver.page_source
        return self.driver.find_elements(By.CLASS_NAME, value="company-jobs-preview-card_companyOtherJobsTitle__cmhU8")

    def compile(self):
        """
        Scrape jobs
        """
        # Retrieve the table of job listings
        groups = self.load_and_filter()
        print(groups)
        curr = groups
        for i in range(len(groups)):
            self.actions.move_to_element(curr[i]).click().perform()


            time.sleep(3)
            curr = self.load_and_filter()
        return
        
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


if __name__ == '__main__':
    js = JobScraper()
    js.compile()