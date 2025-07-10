# SPDX-FileCopyrightText: 2023-present David C Wang <dcwangmit01@gmail.com>
#
# SPDX-License-Identifier: MIT

"""
Amazon Invoice Downloader - Amazon.com specific functionality
"""

from playwright.sync_api import sync_playwright, TimeoutError
from datetime import datetime
import random
import time
import os


def sleep():
    # Add human latency
    # Generate a random sleep time between 3 and 5 seconds
    sleep_time = random.uniform(2, 5)
    # Sleep for the generated time
    time.sleep(sleep_time)


def run_amazon(playwright, args):
    email = args.get('--email')
    if email == '$AMAZON_EMAIL':
        email = os.environ.get('AMAZON_EMAIL')

    password = args.get('--password')
    if password == '$AMAZON_PASSWORD':
        password = os.environ.get('AMAZON_PASSWORD')

    # Get the domain (com or ca)
    domain = args.get('--domain', 'com')

    # Parse date ranges int start_date and end_date
    if args['--date-range']:
        start_date, end_date = args['--date-range'].split('-')
    elif args['--year'] != "<CUR_YEAR>":
        start_date, end_date = args['--year'] + "0101", args['--year'] + "1231"
    else:
        year = str(datetime.now().year)
        start_date, end_date = year + "0101", year + "1231"
    start_date = datetime.strptime(start_date, "%Y%m%d")
    end_date = datetime.strptime(end_date, "%Y%m%d")

    # Debug
    # print(email, password, start_date, end_date)

    # Ensure the location exists for where we will save our downloads
    target_dir = os.getcwd() + "/" + "downloads"
    os.makedirs(target_dir, exist_ok=True)

    # Create a persistent browser context to save login session
    session_dir = os.getcwd() + "/" + "browser_session"
    os.makedirs(session_dir, exist_ok=True)
    
    # Create Playwright context with persistent session
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(
        accept_downloads=True,
        storage_state=session_dir + "/auth_state.json" if os.path.exists(session_dir + "/auth_state.json") else None
    )

    page = context.new_page()
    # Use the selected domain (com or ca)
    amazon_url = f"https://www.amazon.{domain}/"
    page.goto(amazon_url)

    # Check if we're already logged in by looking for account-specific elements
    print("Checking if already logged in...")
    already_logged_in = False
    
    # Look for more reliable signs that we're actually logged in
    # The orders link exists even when not logged in, so we need better indicators
    login_indicators = [
        'span[id="nav-link-accountList-nav-line-1"]',  # "Hello, [Name]" text
        'a[data-nav-role="signin"] >> text="Sign Out"',  # Sign out link
        'a >> text="Sign Out"',  # Sign out link
        'a >> text="Déconnexion"',  # French sign out
        'span >> text="Hello,"',  # Hello greeting (more reliable)
        'span >> text="Bonjour,"'  # French hello greeting
    ]
    
    for indicator in login_indicators:
        try:
            element = page.wait_for_selector(indicator, timeout=3000)  # Reduced timeout
            if element:
                print(f"Found login indicator: {indicator}")
                # Double-check by trying to access orders page directly
                print("Verifying login by testing orders page access...")
                orders_url = f"https://www.amazon.{domain}/gp/css/order-history"
                response = page.goto(orders_url)
                
                # Wait a bit for page to load
                time.sleep(2)
                
                # Check if we're redirected to login or if orders page loads
                current_url = page.url
                if "signin" in current_url or "login" in current_url or "ap/" in current_url:
                    print("Orders page redirected to login - session expired")
                    already_logged_in = False
                    # Go back to main page for login
                    page.goto(f"https://www.amazon.{domain}/")
                    break
                else:
                    try:
                        # Look for orders page elements
                        page.wait_for_selector('select#time-filter', timeout=5000)
                        print("Successfully accessed orders page - already logged in!")
                        already_logged_in = True
                        break
                    except:
                        print("Orders page did not load properly - not logged in")
                        already_logged_in = False
                        # Go back to main page for login
                        page.goto(f"https://www.amazon.{domain}/")
                        break
        except:
            continue
    
    if not already_logged_in:
        print("Not logged in, proceeding with login process...")
        
        # Go to main page if not already there
        if page.url != f"https://www.amazon.{domain}/":
            page.goto(f"https://www.amazon.{domain}/")
        
        # Sometimes, we are interrupted by a bot check, so let the user solve it
        print("Navigating to Amazon sign-in page...")
        page.wait_for_selector('span >> text=Hello, sign in', timeout=60000).click()  # 1 minute timeout
        sleep()

        if email:
            print(f"Entering email: {email}")
            # Wait for email field to be available with multiple selectors
            email_selectors = [
                'input[name="email"]',
                'input[type="email"]', 
                '#ap_email',
                'input[id="ap_email"]',
                'input[autocomplete="email"]'
            ]
            
            email_field = None
            for selector in email_selectors:
                try:
                    print(f"Looking for email field with selector: {selector}")
                    page.wait_for_selector(selector, timeout=10000)  # 10 seconds per selector
                    email_field = page.query_selector(selector)
                    if email_field:
                        print(f"Found email field with selector: {selector}")
                        break
                except TimeoutError:
                    print(f"Email field not found with selector: {selector}")
                    continue
            
            # Fallback to playwright's built-in label selector
            if not email_field:
                try:
                    print("Trying label-based email field selection...")
                    email_field = page.get_by_label("Email")
                    if email_field:
                        print("Found email field using label selector")
                except:
                    print("Label-based email field selection failed")
            
            if email_field:
                try:
                    email_field.click()
                    email_field.fill(email)
                    print("Email entered successfully")
                except Exception as e:
                    print(f"Error entering email: {e}")
                    print("Please enter the email manually in the browser")
            else:
                print("Could not find email field - please enter manually")
                print("Waiting 30 seconds for you to enter the email...")
                time.sleep(30)
            
            # Wait for and click Continue button
            continue_selectors = [
                'input[id="continue"]',
                'input[type="submit"]',
                'button[type="submit"]',
                'input[name="continue"]'
            ]
            
            continue_button = None
            for selector in continue_selectors:
                try:
                    print(f"Looking for continue button with selector: {selector}")
                    page.wait_for_selector(selector, timeout=10000)
                    continue_button = page.query_selector(selector)
                    if continue_button:
                        print(f"Found continue button with selector: {selector}")
                        break
                except TimeoutError:
                    print(f"Continue button not found with selector: {selector}")
                    continue
            
            # Fallback to playwright's built-in role selector
            if not continue_button:
                try:
                    print("Trying role-based continue button selection...")
                    continue_button = page.get_by_role("button", name="Continue")
                    if continue_button:
                        print("Found continue button using role selector")
                except:
                    print("Role-based continue button selection failed")
            
            if continue_button:
                try:
                    continue_button.click()
                    print("Continue button clicked")
                except Exception as e:
                    print(f"Error clicking continue button: {e}")
                    print("Please click the continue button manually")
            else:
                print("Could not find continue button - please click manually")
                print("Waiting 10 seconds for you to click the continue button...")
                time.sleep(10)
            
            sleep()

        if password:
            print("Entering password...")
            # Wait for password field to be available with multiple selectors
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]', 
                '#ap_password',
                'input[id="ap_password"]',
                'input[autocomplete="current-password"]'
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    print(f"Looking for password field with selector: {selector}")
                    page.wait_for_selector(selector, timeout=10000)  # 10 seconds per selector
                    password_field = page.query_selector(selector)
                    if password_field:
                        print(f"Found password field with selector: {selector}")
                        break
                except TimeoutError:
                    print(f"Password field not found with selector: {selector}")
                    continue
            
            # Fallback to playwright's built-in label selector
            if not password_field:
                try:
                    print("Trying label-based password field selection...")
                    password_field = page.get_by_label("Password")
                    if password_field:
                        print("Found password field using label selector")
                except:
                    print("Label-based password field selection failed")
            
            if password_field:
                try:
                    password_field.click()
                    password_field.fill("")  # Clear any existing content by filling with empty string
                    password_field.fill(password)
                    print("Password entered successfully")
                except Exception as e:
                    print(f"Error entering password: {e}")
                    print("Please enter the password manually in the browser")
            else:
                print("Could not find password field - please enter manually")
                print("Waiting 30 seconds for you to enter the password...")
                time.sleep(30)
            
            # Check "Keep me signed in" if available
            keep_signed_in_selectors = [
                'input[name="rememberMe"]',
                '#ap_check_signin_session_checkbox',
                'input[name="keep_me_signed_in"]',
                'input[type="checkbox"][name*="remember"]'
            ]
            
            for selector in keep_signed_in_selectors:
                try:
                    keep_signed_in = page.query_selector(selector)
                    if keep_signed_in:
                        keep_signed_in.check()
                        print(f"Keep me signed in checked using selector: {selector}")
                        break
                except:
                    continue
            
            # Wait for and click Sign in button
            signin_selectors = [
                'input[id="signInSubmit"]',
                'input[type="submit"]',
                'button[type="submit"]',
                'input[name="signIn"]',
                'button >> text="Sign in"',
                'input[value*="Sign"]'
            ]
            
            signin_button = None
            for selector in signin_selectors:
                try:
                    print(f"Looking for sign in button with selector: {selector}")
                    page.wait_for_selector(selector, timeout=10000)
                    signin_button = page.query_selector(selector)
                    if signin_button:
                        print(f"Found sign in button with selector: {selector}")
                        break
                except TimeoutError:
                    print(f"Sign in button not found with selector: {selector}")
                    continue
            
            # Fallback to playwright's built-in role selector
            if not signin_button:
                try:
                    print("Trying role-based sign in button selection...")
                    signin_button = page.get_by_role("button", name="Sign in")
                    if signin_button:
                        print("Found sign in button using role selector")
                except:
                    print("Role-based sign in button selection failed")
            
            if signin_button:
                try:
                    signin_button.click()
                    print("Sign in button clicked")
                except Exception as e:
                    print(f"Error clicking sign in button: {e}")
                    print("Please click the sign in button manually")
            else:
                print("Could not find sign in button - please click manually")
                print("Waiting 10 seconds for you to click the sign in button...")
                time.sleep(10)

        # Wait for login to complete - this handles OTP/2FA if required
        # The user has up to 5 minutes to complete any two-factor authentication
        print("Waiting for login to complete...")
        print("If Amazon asks for OTP/2FA, please complete it in the browser window.")
        print("You have up to 5 minutes to complete the authentication process.")
        
        # First, check if we're on an OTP/2FA page and wait for it to complete
        otp_selectors = [
            'input[name="otpCode"]',
            'input[name="code"]',
            'input[id="auth-mfa-otpcode"]',
            'input[placeholder*="code"]',
            'input[placeholder*="Code"]',
            'input[aria-label*="code"]',
            'input[aria-label*="Code"]',
            'form[name="challenge"]',
            'div[data-testid="auth-mfa"]',
            'h1 >> text="Two-Step Verification"',
            'h1 >> text="Enter the code"',
            'h1 >> text="Entrez le code"',  # French
            'span >> text="We sent a code"',
            'span >> text="Nous avons envoyé"'  # French
        ]
        
        # Check if we're on an OTP page
        on_otp_page = False
        for selector in otp_selectors:
            try:
                element = page.wait_for_selector(selector, timeout=5000)  # 5 second check
                if element:
                    print(f"Detected OTP/2FA page with selector: {selector}")
                    on_otp_page = True
                    break
            except TimeoutError:
                continue
        
        if on_otp_page:
            print("OTP/2FA page detected. Please complete the verification process.")
            print("Waiting for you to complete OTP/2FA...")
            
            # Wait for OTP page to disappear (user completes OTP)
            otp_completed = False
            start_time = time.time()
            timeout_seconds = 300  # 5 minutes
            
            while not otp_completed and (time.time() - start_time) < timeout_seconds:
                # Check if we're still on OTP page
                still_on_otp = False
                for selector in otp_selectors:
                    try:
                        element = page.wait_for_selector(selector, timeout=2000)  # 2 second check
                        if element:
                            still_on_otp = True
                            break
                    except TimeoutError:
                        continue
                
                if not still_on_otp:
                    print("OTP/2FA completed successfully!")
                    otp_completed = True
                else:
                    print("Still waiting for OTP/2FA completion...")
                    time.sleep(10)  # Wait 10 seconds before checking again
            
            if not otp_completed:
                print("ERROR: Timeout waiting for OTP/2FA completion.")
                print("Please complete the OTP/2FA process and try again.")
                context.close()
                browser.close()
                return
        else:
            print("No OTP/2FA page detected, proceeding with login...")
        
        # Save authentication state for future runs
        print("Saving login session for future use...")
        context.storage_state(path=session_dir + "/auth_state.json")
        print("Login session saved! You won't need to log in again for future runs.")
    else:
        print("Using saved login session, skipping login process...")
    
    # Navigate directly to the orders page instead of trying to find and click the link
    print("Navigating to orders page...")
    orders_url = f"https://www.amazon.{domain}/gp/css/order-history"
    page.goto(orders_url)
    
    # Wait for the orders page to load
    print("Waiting for orders page to load...")
    try:
        page.wait_for_selector('select#time-filter', timeout=60000)  # Wait for the year filter to appear
        print("Orders page loaded successfully!")
    except TimeoutError:
        print("ERROR: Orders page did not load properly.")
        print("Please check if you are logged in and try again.")
        context.close()
        browser.close()
        return
    
    sleep()

    # Get a list of years from the select options
    select = page.query_selector('select#time-filter')
    years = select.inner_text().split("\n")  # skip the first two text options

    # Filter years to include only numerical years (YYYY)
    years = [year for year in years if year.isnumeric()]

    # Filter years to the include only the years between start_date and end_date inclusively
    years = [year for year in years if start_date.year <= int(year) <= end_date.year]
    years.sort(reverse=True)

    # Year Loop (Run backwards through the time range from years to pages to orders)
    for year in years:
        # Select the year in the order filter
        page.select_option('form[action="/your-orders/orders"] select#time-filter', value=f"year-{year}")
        sleep()

        # Page Loop
        first_page = True
        done = False
        while not done:
            # Go to the next page pagination, and continue downloading
            #   if there is not a next page then break
            try:
                if first_page:
                    first_page = False
                else:
                    # Wait for next page link with longer timeout
                    page.wait_for_selector('a >> text="Next →"', timeout=60000)
                    page.get_by_role("link", name="Next →").click()
                sleep()  # sleep after every page load
            except TimeoutError:
                # There are no more pages
                print("No more pages found, moving to next year")
                break

            # Order Loop
            order_cards = page.query_selector_all(".order-card.js-order-card")
            for order_card in order_cards:
                # Parse the order card to create the date and file_name
                spans = order_card.query_selector_all("span")
                date = datetime.strptime(spans[1].inner_text(), "%B %d, %Y")
                total = spans[3].inner_text().replace("$", "").replace(",", "")  # remove dollar sign and commas
                orderid = spans[9].inner_text()
                date_str = date.strftime("%Y%m%d")
                file_name = f"{target_dir}/{date_str}_{total}_amazon_{orderid}.pdf"

                if date > end_date:
                    continue
                elif date < start_date:
                    done = True
                    break

                if os.path.isfile(file_name):
                    print(f"File [{file_name}] already exists")
                else:
                    print(f"Saving file [{file_name}]")
                    
                    # Try to find the invoice link with multiple possible text variations
                    invoice_link = None
                    possible_link_texts = [
                        'View invoice',
                        'Invoice',
                        'View Invoice',
                        'Voir la facture',  # French for amazon.ca
                        'Facture'  # French for amazon.ca
                    ]
                    
                    for link_text in possible_link_texts:
                        link_element = order_card.query_selector(f'xpath=//a[contains(text(), "{link_text}")]')
                        if link_element:
                            invoice_link = link_element
                            break
                    
                    if invoice_link:
                        try:
                            print(f"Clicking invoice button to download PDF...")
                            
                            # Start waiting for download before clicking
                            with page.expect_download() as download_info:
                                invoice_link.click()
                            
                            # Get the download object
                            download = download_info.value
                            
                            # Save the download with our desired filename
                            print(f"PDF download started, saving as: {file_name}")
                            download.save_as(file_name)
                            print(f"Invoice downloaded and saved successfully!")
                            
                        except Exception as e:
                            print(f"Error downloading invoice for order {orderid}: {str(e)}")
                            print("This might be due to:")
                            print("- Order doesn't have an invoice available")
                            print("- Session timeout or authentication issue") 
                            print("- The invoice link doesn't trigger a download")
                    else:
                        print(f"Warning: No invoice link found for order {orderid} - this order may not have an invoice available")

    # Close the browser
    context.close()
    browser.close()


def run_amazon_downloader(args):
    """Main entry point for Amazon invoice downloader"""
    with sync_playwright() as playwright:
        run_amazon(playwright, args) 