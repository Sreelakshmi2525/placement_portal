# jobs/job_scraper.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()
class LinkedInJobScraper:
    def __init__(self, email=None, password=None, chromedriver_path=None):
        """
        Initialize the LinkedIn job scraper with credentials.
        """
        self.email = email if email else os.getenv("LINKEDIN_EMAIL", "")
        self.password = password if password else os.getenv("LINKEDIN_PASSWORD", "")

        
        # Set up Chrome options
        chrome_options = Options()
        # Uncomment the line below to run Chrome in headless mode
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        
        # Disable WebGL and accelerated 2D canvas to prevent tensor errors
        chrome_options.add_argument("--disable-webgl")
        chrome_options.add_argument("--disable-accelerated-2d-canvas")
        chrome_options.add_argument("--disable-gpu")
        
        # Set user agent to appear as a regular browser
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            if chromedriver_path:
                service = Service(chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # Use webdriver-manager
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set a longer wait time to handle slow page loads
            self.wait = WebDriverWait(self.driver, 50)
        except Exception as e:
            print(f"Error initializing Chrome driver: {e}")
            self.driver = None
    
    def login(self):
        """Log in to LinkedIn."""
        if not self.driver:
            print("Driver not initialized")
            return False
            
        print("Logging in to LinkedIn...")
        try:
            self.driver.get("https://www.linkedin.com/login")
            
            # Wait for the login page to load
            username_input = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            password_input = self.wait.until(EC.presence_of_element_located((By.ID, "password")))
            
            # Enter credentials
            username_input.send_keys(self.email)
            password_input.send_keys(self.password)
            
            # Click the login button
            password_input.send_keys(Keys.RETURN)
            
            # Wait for login to complete
            try:
                self.wait.until(lambda driver: "feed" in driver.current_url or "checkpoint" in driver.current_url or "dashboard" in driver.current_url)
                print("Successfully logged in!")
                return True
                
            except TimeoutException:
                print("Login failed or took too long.")
                return False
                
        except Exception as e:
            print(f"Error during login: {e}")
            return False
    
    def get_jobs(self, keywords, location="", max_jobs=10):
        """
        Search for jobs and collect information including descriptions.
        """
        if not self.driver:
            print("Driver not initialized")
            return []
            
        print(f"Searching for jobs with keywords: '{keywords}', location: '{location}'")
        
        # Build a direct URL with search parameters
        base_url = "https://www.linkedin.com/jobs/search/?"
        params = []
        
        # Add keywords
        params.append(f"keywords={keywords.replace(' ', '%20')}")
        
        # Add location
        if location:
            params.append(f"location={location.replace(' ', '%20')}")
        
        # Add additional parameters for better results
        params.append("trk=public_jobs_jobs-search-bar_search-submit")
        params.append("position=1")
        params.append("pageNum=0")
        
        # Build the complete URL
        search_url = base_url + "&".join(params)
        print(f"Using search URL: {search_url}")
        
        # Navigate to the search URL
        try:
            self.driver.get(search_url)
            time.sleep(5)  # Wait for page to load
            
            # Find job listings
            jobs_found = 0
            job_data_list = []
            
            # Try finding job cards
            job_cards = []
            selectors = [
                "li.jobs-search-results__list-item",
                "li.job-search-card",
                "li.occludable-update",
                ".job-card-container",
                ".job-card-list__entity-lockup"
            ]
            
            for selector in selectors:
                try:
                    job_cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if job_cards:
                        print(f"Found {len(job_cards)} job listings with selector: {selector}")
                        break
                except Exception:
                    pass
            
            if job_cards:
                # Process job cards
                for i, card in enumerate(job_cards):
                    if jobs_found >= max_jobs:
                        break
                        
                    try:
                        # Extract job title and URL
                        job_title = "Unknown"
                        job_url = ""
                        try:
                            title_elem = card.find_element(By.CSS_SELECTOR, ".job-card-list__title, .job-card-container__link, h3, a[data-control-name='job_card_title']")
                            job_title = title_elem.text.strip()
                            job_url = title_elem.get_attribute("href")
                        except:
                            # Try alternative approach
                            try:
                                all_links = card.find_elements(By.TAG_NAME, "a")
                                for link in all_links:
                                    href = link.get_attribute("href")
                                    if href and "/jobs/view/" in href:
                                        job_url = href
                                        if not job_title or job_title == "Unknown":
                                            job_title = link.text.strip()
                                        break
                            except:
                                continue
                        
                        # Extract company name
                        company_name = "Unknown"
                        try:
                            company_elem = card.find_element(By.CSS_SELECTOR, ".job-card-container__company-name, .job-card-container__primary-description, a[data-control-name='job_card_company']")
                            company_name = company_elem.text.strip()
                        except:
                            pass
                        
                        # Extract location
                        job_location = location if location else "Unknown"
                        try:
                            location_elem = card.find_element(By.CSS_SELECTOR, ".job-card-container__metadata-item, .job-card-container__location")
                            job_location = location_elem.text.strip()
                        except:
                            pass
                        
                        # Get job description by opening the job page
                        job_description = ""
                        if job_url:
                            try:
                                # Open a new tab with the job page
                                self.driver.execute_script("window.open(arguments[0]);", job_url)
                                
                                # Switch to the new tab
                                self.driver.switch_to.window(self.driver.window_handles[1])
                                
                                # Wait for the job description to load
                                time.sleep(3)
                                
                                # Try to find the job description
                                description_selectors = [
                                    ".description__text",
                                    ".show-more-less-html__markup",
                                    ".jobs-description__content",
                                    ".jobs-box__html-content"
                                ]
                                
                                for desc_selector in description_selectors:
                                    try:
                                        description_elem = self.driver.find_element(By.CSS_SELECTOR, desc_selector)
                                        job_description = description_elem.text.strip()
                                        if job_description:
                                            break
                                    except:
                                        pass
                                
                                # Extract salary information if available
                                salary_info = "Check job listing for details"
                                try:
                                    salary_elem = self.driver.find_element(By.CSS_SELECTOR, ".jobs-unified-top-card__job-insight:contains('salary'), .compensation__salary")
                                    if salary_elem:
                                        salary_info = salary_elem.text.strip()
                                except:
                                    pass
                                
                                # Close the tab and switch back to the main tab
                                self.driver.close()
                                self.driver.switch_to.window(self.driver.window_handles[0])
                                
                            except Exception as e:
                                print(f"Error fetching job details: {e}")
                                # Close any extra tabs and switch back to main
                                if len(self.driver.window_handles) > 1:
                                    self.driver.close()
                                    self.driver.switch_to.window(self.driver.window_handles[0])
                        
                        # If no description was found, use a placeholder
                        if not job_description:
                            job_description = f"Click the job link to view the full description. This job was found on LinkedIn with the search term: {keywords}."
                        
                        # Add to results if we have at least a title and URL
                        if job_title and job_title != "Unknown" and job_url:
                            job_data = {
                                "title": job_title,
                                "company": company_name,
                                "location": job_location,
                                "url": job_url,
                                "description": job_description,
                                "salary": salary_info
                            }
                            job_data_list.append(job_data)
                            jobs_found += 1
                            print(f"Job {jobs_found}: {job_title} at {company_name}")
                    except Exception as e:
                        print(f"Error processing job card {i+1}: {e}")
            else:
                print("No job cards found with the standard selectors.")
            
            print(f"Total jobs collected: {len(job_data_list)}")
            return job_data_list
        
        except Exception as e:
            print(f"Error during job search: {e}")
            return []
    
    def close(self):
        """Close the browser and clean up."""
        if self.driver:
            self.driver.quit()
            print("Browser closed.")