# jobs/job_application_bot.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from dotenv import load_dotenv
load_dotenv()

import os


class JobApplicationBot:
    def __init__(self, email=None, password=None, chromedriver_path=None):
        """
        Initialize the job application bot.
        """
        self.email = email if email else os.getenv("LINKEDIN_EMAIL", "")
        self.password = password if password else os.getenv("LINKEDIN_PASSWORD", "")        
        # Set up Chrome options
        chrome_options = Options()
        # Uncomment the line below to run Chrome in headless mode for production
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        
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
            self.wait = WebDriverWait(self.driver, 20)
        except Exception as e:
            print(f"Error initializing Chrome driver: {e}")
            self.driver = None
    
    def login_to_linkedin(self):
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
            username_input.send_keys(self.linkedin_email)
            password_input.send_keys(self.linkedin_password)
            
            # Click the login button
            password_input.send_keys(Keys.RETURN)
            
            # Wait for login to complete
            try:
                self.wait.until(lambda driver: "feed" in driver.current_url or "checkpoint" in driver.current_url or "dashboard" in driver.current_url)
                print("Successfully logged in to LinkedIn!")
                return True
                
            except TimeoutException:
                print("Login to LinkedIn failed or took too long.")
                return False
                
        except Exception as e:
            print(f"Error during LinkedIn login: {e}")
            return False
    
    def apply_to_job(self, job_url, student_info):
        """
        Apply to a job on LinkedIn with student information.
        
        Args:
            job_url (str): URL of the job on LinkedIn
            student_info (dict): Student information for application
                                 (name, email, phone, resume_path, etc.)
        
        Returns:
            bool: Whether the application was successful
            str: Status message about the application
        """
        if not self.driver:
            return False, "Driver not initialized"
        
        # Make sure we're logged in to LinkedIn
        if "linkedin.com" not in self.driver.current_url:
            login_success = self.login_to_linkedin()
            if not login_success:
                return False, "Failed to log in to LinkedIn"
        
        try:
            # Navigate to the job page
            print(f"Navigating to job: {job_url}")
            self.driver.get(job_url)
            time.sleep(3)  # Wait for page to load
            
            # Check if it's a LinkedIn job
            if "linkedin.com/jobs/view" not in self.driver.current_url:
                return False, "Not a LinkedIn job posting"
            
            # Look for the apply button
            apply_button = None
            apply_button_selectors = [
                "button.jobs-apply-button",
                "button.jobs-s-apply",
                ".jobs-apply-button",
                ".jobs-s-apply button",
                "button[data-control-name='jobdetails_topcard_inapply']"
            ]
            
            for selector in apply_button_selectors:
                try:
                    apply_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if apply_button:
                        break
                except:
                    continue
            
            if not apply_button:
                return False, "Could not find apply button"
            
            # Click the apply button
            apply_button.click()
            time.sleep(3)
            
            # Check if there's an existing application
            try:
                existing_application = self.driver.find_element(By.XPATH, "//h2[contains(text(), 'Application submitted')]")
                if existing_application:
                    return True, "You've already applied to this job"
            except:
                pass
            
            # Here's where we'd fill out the application form
            # This is complex and varies widely between job postings
            # The following is a simplified version
            
            try:
                # Check for "Easy Apply" form
                form_fields = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='email'], input[type='tel']")
                
                if form_fields:
                    print("Found application form fields")
                    
                    # Fill phone number field
                    phone_fields = self.driver.find_elements(By.CSS_SELECTOR, "input[type='tel']")
                    for field in phone_fields:
                        field.clear()
                        field.send_keys(student_info.get('phone', ''))
                    
                    # Fill email field if empty
                    email_fields = self.driver.find_elements(By.CSS_SELECTOR, "input[type='email']")
                    for field in email_fields:
                        if not field.get_attribute('value'):
                            field.clear()
                            field.send_keys(student_info.get('email', ''))
                
                # Upload resume if requested
                try:
                    resume_upload = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                    if resume_upload and student_info.get('resume_path'):
                        resume_upload.send_keys(student_info.get('resume_path'))
                        time.sleep(2)
                except:
                    print("Resume upload not found or not required")
                
                # Try to find the Next or Submit buttons
                next_buttons = []
                button_texts = ["Next", "Review", "Submit application", "Continue", "Send application"]
                
                for text in button_texts:
                    try:
                        buttons = self.driver.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
                        next_buttons.extend(buttons)
                    except:
                        pass
                
                if next_buttons:
                    print(f"Found {len(next_buttons)} next/submit buttons")
                    
                    # Click through the application process
                    for btn in next_buttons:
                        try:
                            btn.click()
                            time.sleep(2)
                        except:
                            print(f"Could not click button: {btn.text}")
                    
                    # Check if the application was submitted
                    try:
                        confirmation = self.driver.find_element(By.XPATH, "//h2[contains(text(), 'Application submitted')]")
                        if confirmation:
                            return True, "Application submitted successfully!"
                    except:
                        pass
                    
                    return True, "Application process completed (status unknown)"
                else:
                    return False, "Could not find submit button"
                
            except Exception as e:
                print(f"Error during application: {e}")
                return False, f"Error during application: {str(e)}"
            
        except Exception as e:
            print(f"Error applying to job: {e}")
            return False, f"Error: {str(e)}"
        finally:
            try:
                # Try to close any dialogs
                close_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Dismiss']")
                for btn in close_buttons:
                    btn.click()
            except:
                pass
    
    def close(self):
        """Close the browser and clean up."""
        if self.driver:
            self.driver.quit()
            print("Browser closed.")