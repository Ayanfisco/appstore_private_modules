# Paystack Payment Provider for Odoo

[![Paystack](https://img.shields.io/badge/Paystack-Certified-brightgreen.svg)](https://paystack.com/)
[![Odoo Version](https://img.shields.io/badge/Odoo-18.0-blue.svg)](https://www.odoo.com/)
[![License: OPL-3](https://img.shields.io/badge/license-OPL--3-blue.svg)](https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#odoo-apps)

## Overview

This module integrates Paystack payment gateway with Odoo, enabling businesses in Africa to accept payments online through various payment methods including cards, bank transfers, and mobile money.

### Key Features

- 🌍 **Multi-Currency Support**

  - Nigerian Naira (NGN)
  - Ghanaian Cedi (GHS)
  - South African Rand (ZAR)
  - Kenyan Shilling (KES)
  - US Dollar (USD)

- 💳 **Payment Methods**

  - Credit/Debit Cards (Visa, Mastercard, Verve)
  - Bank Transfers
  - USSD
  - Mobile Money

- 🔒 **Security**

  - PCI-DSS Level 1 compliant
  - Secure transaction processing
  - Real-time fraud screening

- 🔄 **Advanced Features**
  - Webhook integration for real-time updates
  - Automated payment verification
  - Detailed transaction reporting
  - Instant settlement options

## Installation

1. Download the module and add it to your Odoo addons directory.
2. Update the module list in your Odoo instance.
3. Look for "Paystack Payment Provider" in the apps list.
4. Click install.

## Configuration

1. Go to Website ‣ Configuration ‣ Payment Providers
2. Find and activate Paystack in the list of providers
3. Configure your Paystack credentials:
   - Enter your Secret Key
   - Enter your Public Key
   - Choose the payment environment (Test/Live)

## Usage

1. **For Customers:**

   - Select Paystack as payment method during checkout
   - Get redirected to secure Paystack payment page
   - Complete payment using preferred method
   - Return automatically to merchant site

2. **For Merchants:**
   - Monitor transactions in real-time
   - View detailed payment information
   - Process refunds when needed
   - Access comprehensive reporting

## Support

- For module support, please create an issue on the GitHub repository
- For Paystack-specific issues, contact [Paystack Support](https://paystack.com/support)
- For customizations and consulting, contact the author

## Credits

Developed by [Your Company Name] - [Your Website]

## License

This module is published under the OPL-3 license.

## Contributors

- Your Name <your.email@example.com>

---

For more information about Paystack's services, visit [Paystack's Website](https://paystack.com).
