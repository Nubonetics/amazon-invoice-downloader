# SPDX-FileCopyrightText: 2023-present David C Wang <dcwangmit01@gmail.com>
#
# SPDX-License-Identifier: MIT

"""
Multi-Website Invoice Downloader

Usage:
  amazon-invoice-downloader \
    [--website=<website>] \
    [--domain=<domain>] \
    [--email=<email> --password=<password>] \
    [--year=<YYYY> | --date-range=<YYYYMMDD-YYYYMMDD>]
  amazon-invoice-downloader (-h | --help)

Website Options:
  --website=<website>      Website to download from [default: amazon].
  --domain=<domain>        Amazon domain to use (com or ca). If not specified, an interactive menu will be shown.

Login Options:
  --email=<email>          Login email  [default: $AMAZON_EMAIL].
  --password=<password>    Login password  [default: $AMAZON_PASSWORD].

Date Range Options:
  --date-range=<YYYYMMDD-YYYYMMDD>  Start and end date range
  --year=<YYYY>            Year, formatted as YYYY  [default: <CUR_YEAR>].

Options:
  -h --help                Show this screen.

Examples:
  amazon-invoice-downloader --website=amazon --domain=com --year=2022  # This uses env vars $AMAZON_EMAIL and $AMAZON_PASSWORD
  amazon-invoice-downloader --website=amazon --domain=ca --year=2022   # Download from amazon.ca
  amazon-invoice-downloader --website=amazon --year=2022               # Interactive menu will ask for domain choice
  amazon-invoice-downloader --website=amazon --date-range=20220101-20221231
  amazon-invoice-downloader --email=user@example.com --password=secret  # Interactive menu will ask for domain choice
  amazon-invoice-downloader --email=user@example.com --password=secret --year=2022
  amazon-invoice-downloader --email=user@example.com --password=secret --date-range=20220101-20221231
"""

from amazon_invoice_downloader.__about__ import __version__
from amazon_invoice_downloader.cli.amazon import run_amazon_downloader

import sys
from docopt import docopt


def show_domain_menu():
    """Show an interactive menu to choose the Amazon domain"""
    print("\n" + "="*50)
    print("Amazon Invoice Downloader")
    print("="*50)
    print("Please choose your Amazon domain:")
    print("1. Amazon.com (US)")
    print("2. Amazon.ca (Canada)")
    print("="*50)
    
    while True:
        try:
            choice = input("Enter your choice (1 or 2): ").strip()
            if choice == '1':
                return 'com'
            elif choice == '2':
                return 'ca'
            else:
                print("Invalid choice. Please enter 1 or 2.")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            sys.exit(0)


def amazon_invoice_downloader():
    args = docopt(__doc__)
    
    # Get the website to download from
    website = args.get('--website', 'amazon')
    
    # Get the domain (com or ca)
    domain = args.get('--domain')
    
    # If no domain is specified, show interactive menu
    if not domain:
        domain = show_domain_menu()
    
    # Validate domain
    if domain not in ['com', 'ca']:
        print(f"Error: Unsupported domain '{domain}'")
        print("Currently supported domains: com, ca")
        sys.exit(1)
    
    # Update args with the selected domain
    args['--domain'] = domain
    
    print(f"Selected domain: amazon.{domain}")
    
    # Route to the appropriate website module
    if website == 'amazon':
        run_amazon_downloader(args)
    else:
        print(f"Error: Unsupported website '{website}'")
        print("Currently supported websites: amazon")
        sys.exit(1)
