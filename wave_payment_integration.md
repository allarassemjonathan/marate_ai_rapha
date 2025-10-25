# Wave Mobile Payment Integration Guide

## Overview
Wave Business APIs provide a programmatic means to work with your Wave business account. By using these REST APIs you can receive payments, send money to your clients, check the balance on your wallet and perform automated reconciliation.

**Requirements:** You need a Wave Business Account to use these APIs.

## Base URL
All API endpoints are relative to: `https://api.wave.com`

---

## Available APIs

### 1. Checkout API (Primary for Payment Processing)
- **Purpose:** Allow users from website/mobile app to send payments
- **Main Endpoint:** `/v1/checkout/sessions`
- **Documentation:** https://docs.wave.com/checkout

### 2. Balance & Reconciliation API
- **Purpose:** Check wallet balance, retrieve transaction history, and perform automated reconciliation
- **Main Endpoints:** `/v1/balance`, `/v1/transactions`, `/v1/transactions/:id/refund`
- **Documentation:** https://docs.wave.com/balance-api

### 3. Payout API  
- **Purpose:** Send money from business to recipients (individuals or other businesses)
- **Main Endpoints:** `/v1/payout`, `/v1/payout-batch`, `/v1/payout/:id/reverse`
- **Documentation:** https://docs.wave.com/payout

### 4. Aggregated Merchants API
- **Purpose:** Manage multiple merchant identities under one aggregator account
- **Main Endpoints:** `/v1/aggregated_merchants` (CRUD operations)
- **Access:** Limited to selected aggregator partners only
- **Documentation:** https://docs.wave.com/aggregated-merchants

### 5. Webhooks
- **Purpose:** Receive real-time notifications about payment events
- **Documentation:** https://docs.wave.com/webhook

---

## Authentication

### API Key Management
- Manage API keys in [Wave Business Portal](https://business.wave.com/dev-portal)
- Only Admin users can access Developer section
- Each API key is bound to a single business wallet
- Keys can be scoped to specific APIs

### Authentication Header
```bash
Authorization: Bearer wave_sn_prod_YhUNb9d...i4bA6
```

### Security Notes
- API keys must be kept secret
- Never store in client-side code
- All requests must be sent over HTTPS
- Keys can be revoked if compromised

---

## Checkout API - Payment Processing

### Create Payment Session
**Endpoint:** `POST /v1/checkout/sessions`

**Required Parameters:**
- `amount` (string): Total amount to collect (e.g., "1000")
- `currency` (string): ISO 4217 currency code (use "XOF" for West African Franc)
- `success_url` (string): HTTPS URL for successful payment redirect
- `error_url` (string): HTTPS URL for failed payment redirect

**Optional Parameters:**
- `client_reference` (string, max 255 chars): Your system's unique identifier
- `restrict_payer_mobile` (string): Restrict payment to specific phone number (E.164 format)
- `aggregated_merchant_id` (string): For aggregator businesses only

**Example Request:**
```bash
curl -X POST \
-H 'Authorization: Bearer wave_sn_prod_YhUNb9d...i4bA6' \
-H 'Content-Type: application/json' \
-d '{
      "amount": "1000",
      "currency": "XOF",
      "error_url": "https://example.com/error",
      "success_url": "https://example.com/success",
      "client_reference": "order_12345"
    }' \
https://api.wave.com/v1/checkout/sessions
```

### Response - Checkout Session Object
```json
{
  "id": "cos-18qq25rgr100a",
  "amount": "1000",
  "checkout_status": "open|complete|expired",
  "payment_status": "processing|cancelled|succeeded",
  "client_reference": "order_12345",
  "currency": "XOF",
  "error_url": "https://example.com/error",
  "success_url": "https://example.com/success",
  "business_name": "Your Business Name",
  "transaction_id": "TDH5TEWTLFE",
  "wave_launch_url": "https://pay.wave.com/c/cos-18qq25rgr100a",
  "when_created": "2021-12-08T10:13:04Z",
  "when_expires": "2021-12-09T10:13:04Z",
  "when_completed": "2021-12-08T10:15:32Z"
}
```

### Payment Flow
1. Create checkout session via API
2. Redirect user to `wave_launch_url` (must be opened in browser, not webview)
3. User completes payment in Wave app
4. User redirected to success_url or error_url
5. Webhook notification sent to your server (recommended for reliability)

### Other Checkout Endpoints
- `GET /v1/checkout/sessions/:id` - Retrieve specific session
- `GET /v1/checkout/sessions?transaction_id=T_xxx` - Get by transaction ID
- `GET /v1/checkout/sessions/search?client_reference=xxx` - Search by reference
- `POST /v1/checkout/sessions/:id/expire` - Manually expire session
- `POST /v1/checkout/sessions/:id/refund` - Refund payment

---

## Currency and Amount Formatting

### Currency
- Use ISO 4217 codes (XOF for West African Franc)
- **Important:** XOF does not allow decimal places

### Amount Format
- Always strings, never numbers
- Use period (.) as decimal separator
- 0-2 decimal places allowed (except XOF)
- No leading zeros for values ≥ 1
- One leading zero for values < 1
- Examples: "1000", "15.50", "0.99"

---

## Webhooks - Real-time Notifications

### Setup
- Register webhook URLs in [Business Portal](https://business.wave.com/dev-portal/webhooks)
- Choose security strategy (Shared Secret or Signing Secret recommended)
- Select event types to receive

### Security Strategies

#### 1. Shared Secret (Simpler)
```bash
# Webhook receives this header:
Authorization: Bearer wave_sn_WHS_xz4m6g8rjs9bshxy05xj4khcvjv7j3hcp4fbpvv6met0zdrjvezg
```

#### 2. Signing Secret (More secure)
```bash
# Webhook receives this header:
Wave-Signature: t=1639081943,v1=942119aedf9fa377844cf010785fe14ef8478c72af0b73d62ea3941335b526a8
```

### Event Types
- `checkout.session.completed` - Payment successful
- `checkout.session.payment_failed` - Payment failed
- `merchant.payment_received` - Direct merchant payment
- `b2b.payment_received` - Business-to-business payment
- `b2b.payment_failed` - B2B payment failed

### Webhook Event Structure
```json
{
  "id": "EV_QvEZuDSQbLdI",
  "type": "checkout.session.completed",
  "data": {
    "id": "cos-18qq25rgr100a",
    "amount": "1000",
    "checkout_status": "complete",
    "payment_status": "succeeded",
    "client_reference": "order_12345",
    "currency": "XOF",
    "transaction_id": "TDH5TEWTLFE",
    "when_completed": "2021-12-08T10:15:32Z"
  }
}
```

### Webhook Implementation Best Practices
1. **Verify signature** before processing
2. **Respond with HTTP 2xx** immediately
3. **Perform business logic** after responding
4. **Handle duplicates** (idempotent processing)
5. **Handle out-of-order** events
6. **Validate timestamps** (reject old events)

### IP Whitelisting
Whitelist these IPs for enhanced security:
- 104.155.43.220/32
- 34.140.23.175/32
- 34.22.138.147/32
- 34.76.157.22/32
- 34.78.253.137/32
- 34.79.119.200/32
- 35.189.207.30/32
- 35.195.255.192/32
- 35.205.122.113/32
- 35.205.190.121/32
- 35.233.61.130/32
- 35.240.61.196/32
- 35.240.75.65/32
- 35.241.190.127/32
- 35.241.219.1/32

---

## Error Handling

### HTTP Status Codes
- **400** - Bad Request (malformed request)
- **401** - Unauthorized (invalid API key)
- **403** - Forbidden (insufficient permissions)
- **404** - Not Found (resource doesn't exist)
- **422** - Unprocessable Entity (valid format, invalid content)
- **429** - Too Many Requests (rate limit exceeded)
- **500** - Internal Server Error
- **503** - Service Unavailable

### Common Authentication Errors
- `missing-auth-header` - Missing Bearer token
- `invalid-auth` - Cannot process auth header
- `api-key-not-provided` - Missing API key
- `no-matching-api-key` - Key doesn't exist
- `api-key-revoked` - Key has been revoked
- `invalid-wallet` - Wallet cannot use this API
- `disabled-wallet` - Wallet temporarily disabled

### Payment Failure Reasons
- `blocked-account` - Customer account blocked
- `insufficient-funds` - Not enough balance
- `payment-failure` - Technical error
- `payer-mobile-mismatch` - Wrong phone number (when restricted)
- `cross-border-payment-not-allowed` - International transfer restricted
- `customer-age-restricted` - Age verification required
- `kyb-limits-exceeded` - Business account limits reached

---

## Rate Limiting
- APIs are rate limited to prevent abuse
- Receiving 429 errors indicates rate limit exceeded
- Implement exponential backoff for retries

---

## Integration Checklist

### Before Going Live
- [ ] Obtain Wave Business Account
- [ ] Generate API keys in Business Portal
- [ ] Set up webhook endpoints
- [ ] Implement webhook signature verification
- [ ] Test payment flow with small amounts
- [ ] Test error scenarios (insufficient funds, etc.)
- [ ] Implement proper logging and monitoring
- [ ] Set up IP whitelisting if using
- [ ] Test webhook reliability and duplicate handling

### Development Environment
- Use test API keys during development
- Test webhook locally using tools like ngrok
- Use Wave's webhook tester in Business Portal

### Production Considerations
- Store API keys securely (environment variables)
- Implement proper error handling and retries
- Monitor webhook delivery success rates
- Set up alerting for failed payments
- Regular security audits and key rotation

---

## Next Steps for Implementation

1. **Get API Access:**
   - Create Wave Business Account
   - Request API access from Wave support
   - Generate API keys

2. **Backend Integration:**
   - Create endpoint to generate payment sessions
   - Implement webhook receiver endpoint
   - Add signature verification
   - Store payment records in database

3. **Frontend Integration:**
   - Add payment button/form
   - Handle redirect to Wave payment page
   - Process success/error callbacks
   - Display payment status to users

4. **Testing:**
   - Test complete payment flow
   - Verify webhook notifications
   - Test error scenarios
   - Load testing for production

---

## Documentation Links
- [Main API Reference](https://docs.wave.com/business)
- [Checkout API](https://docs.wave.com/checkout)
- [Webhooks](https://docs.wave.com/webhook)
- [Balance API](https://docs.wave.com/balance-api)
- [Payout API](https://docs.wave.com/payout)
- [Business Portal](https://business.wave.com/dev-portal)

---

## Balance & Reconciliation API

### Purpose
Retrieve wallet balance and transaction history for automated reconciliation, reporting, and balance monitoring. **Note:** For real-time payment notifications, use webhooks instead.

### Key Endpoints

#### Get Current Balance
**Endpoint:** `GET /v1/balance`

**Parameters:**
- `include_subaccounts` (optional): Include balances from sub-accounts (for HQ accounts with supervisors/cashiers)

**Response:**
```json
{
  "amount": "10245",
  "currency": "XOF"
}
```

#### Retrieve Transaction History
**Endpoint:** `GET /v1/transactions`

**Parameters:**
- `date` (optional): Specific date (YYYY-MM-DD), defaults to current day
- `after` (optional): Pagination cursor for next page
- `include_subaccounts` (optional): Include sub-account transactions

**Transaction Types:**
- `merchant_payment` - Customer to business payment
- `merchant_payment_refund` - Refund of merchant payment
- `api_checkout` - Payment via Checkout API
- `api_checkout_refund` - Refund of checkout payment
- `api_payout` - Payment via Payout API
- `api_payout_reversal` - Reversal of payout
- `bulk_payment` - Business portal bulk payment
- `b2b_payment` - Business-to-business payment

**Response Fields:**
```json
{
  "page_info": {
    "start_cursor": null,
    "end_cursor": "cursor_string",
    "has_next_page": true
  },
  "date": "2022-11-07",
  "items": [
    {
      "timestamp": "2022-11-07T14:41:15Z",
      "transaction_id": "T_V3TFOUE7VU",
      "transaction_type": "merchant_payment",
      "amount": "99",
      "fee": "1",
      "balance": "10344",
      "currency": "XOF",
      "counterparty_name": "Mame Diop",
      "counterparty_mobile": "+221761110000",
      "client_reference": "order_123",
      "payment_reason": "Medical consultation",
      "checkout_api_session_id": "cos-xxx",
      "custom_fields": {"patient_id": "12345"}
    }
  ]
}
```

#### Refund Transaction
**Endpoint:** `POST /v1/transactions/:transaction_id/refund`

- **Idempotent:** Safe to retry with same transaction ID
- **Returns:** HTTP 200 on success, HTTP 404 if transaction not found
- **Note:** Includes fees in refund

---

## Payout API

### Purpose
Send money from your business wallet to recipients identified by mobile number. Supports individual payouts and bulk processing.

### Key Features
- **Idempotency:** Required for all requests to prevent duplicate transactions
- **Synchronous Processing:** Individual payouts execute immediately
- **Batch Processing:** Asynchronous bulk payouts
- **Reversals:** Can reverse payouts within 3 days

### Individual Payout

#### Create Payout
**Endpoint:** `POST /v1/payout`

**Headers:**
```bash
Authorization: Bearer wave_sn_prod_xxx
Content-Type: application/json
Idempotency-Key: unique-string-per-request
```

**Required Parameters:**
- `currency`: ISO 4217 code (e.g., "XOF")
- `receive_amount`: Amount recipient receives (net of fees)
- `mobile`: Phone number in E.164 format (+221xxxxxxxxx)

**Optional Parameters:**
- `name`: Recipient name (up to 255 chars)
- `national_id`: National ID for verification
- `payment_reason`: Message shown to recipient (up to 40 chars)
- `client_reference`: Your system's reference (up to 255 chars)
- `aggregated_merchant_id`: For aggregator businesses

**Example Request:**
```bash
curl -X POST \
  --url https://api.wave.com/v1/payout \
  -H 'Authorization: Bearer wave_sn_prod_xxx' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: 65f735b4-b44b-429d-b0a8-550701e2393a' \
  -d '{
        "currency": "XOF",
        "receive_amount": "500",
        "name": "Fatou Ndiaye",
        "mobile": "+221555110219",
        "payment_reason": "Medical refund",
        "client_reference": "refund_12345"
      }'
```

**Response:**
```json
{
  "id": "pt-185b5e4b8100c",
  "currency": "XOF",
  "receive_amount": "500",
  "fee": "5",
  "mobile": "+221555110219",
  "name": "Fatou Ndiaye",
  "status": "succeeded|processing|failed",
  "timestamp": "2022-06-20T17:17:11Z",
  "payout_error": null
}
```

### Bulk Payouts

#### Create Payout Batch
**Endpoint:** `POST /v1/payout-batch`

**Example:**
```bash
curl -X POST \
  --url https://api.wave.com/v1/payout-batch \
  -H 'Authorization: Bearer wave_sn_prod_xxx' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: batch-uuid' \
  -d '{
        "payouts": [
          {
            "currency": "XOF",
            "receive_amount": "1000",
            "name": "Patient A",
            "mobile": "+221555110219",
            "client_reference": "refund_001"
          },
          {
            "currency": "XOF", 
            "receive_amount": "1500",
            "name": "Patient B",
            "mobile": "+221555110233",
            "client_reference": "refund_002"
          }
        ]
      }'
```

#### Check Batch Status
**Endpoint:** `GET /v1/payout-batch/:id`

**Response:**
```json
{
  "id": "pb-185skxq8g1006",
  "status": "processing|complete",
  "payouts": [
    {
      "id": "pt-185skxq9g100w",
      "status": "succeeded",
      "currency": "XOF",
      "receive_amount": "1000",
      "fee": "10",
      "mobile": "+221555110219"
    }
  ]
}
```

### Payout Management

#### Retrieve Payout
**Endpoint:** `GET /v1/payout/:id`

#### Search Payouts
**Endpoint:** `GET /v1/payouts/search?client_reference=your_ref`

#### Reverse Payout
**Endpoint:** `POST /v1/payout/:id/reverse`
- **Time Limit:** 3 days from creation
- **Includes:** Reverses amount + fees
- **Idempotent:** Safe to retry

### Payout Error Codes
- `insufficient-funds`: Business wallet lacks balance
- `recipient-limit-exceeded`: Recipient monthly limit reached
- `recipient-account-blocked`: Recipient account blocked
- `recipient-account-inactive`: Recipient account inactive
- `recipient-minor`: Recipient is underage
- `country-mismatch`: Recipient in different country
- `currency-mismatch`: Currency doesn't match wallets

---

## Aggregated Merchants API

### Purpose
**For Aggregator Businesses Only:** Create and manage multiple merchant identities under one account. Each identity can have different business names and fee structures.

### Access Requirements
- Limited to selected aggregator partners
- Contact Wave support to enable access
- Regular businesses don't need this API

### Use Cases
- Payment processors serving multiple merchants
- Fintech companies with sub-merchants
- Platforms with multiple business clients

### Merchant Management

#### Create Aggregated Merchant
**Endpoint:** `POST /v1/aggregated_merchants`

**Required Fields:**
- `name`: Unique merchant name (up to 255 chars)
- `business_description`: Description of business
- `business_type`: "fintech" or "other"

**Optional Fields:**
- `business_registration_identifier`: Registration info
- `business_sector`: Free-form sector description
- `website_url`: Merchant website
- `manager_name`: Business manager name

**Example:**
```bash
curl -X POST \
  --url https://api.wave.com/v1/aggregated_merchants \
  -H 'Authorization: Bearer wave_sn_prod_xxx' \
  -H 'Content-Type: application/json' \
  -d '{
        "name": "Clinic ABC",
        "business_description": "Private medical clinic",
        "business_type": "other",
        "business_sector": "healthcare",
        "website_url": "https://clinic-abc.com",
        "manager_name": "Dr. Smith"
      }'
```

**Response:**
```json
{
  "id": "am-7lks22ap113t4",
  "name": "Clinic ABC",
  "business_type": "other",
  "business_description": "Private medical clinic",
  "payout_fee_structure_name": "one_percent",
  "checkout_fee_structure_name": "one_fifty_bps",
  "is_locked": false,
  "when_created": "2022-06-21T09:56:29Z"
}
```

#### Other Operations
- `GET /v1/aggregated_merchants` - List all merchants
- `GET /v1/aggregated_merchants/:id` - Get specific merchant
- `PUT /v1/aggregated_merchants/:id` - Update merchant (if not locked)
- `DELETE /v1/aggregated_merchants/:id` - Delete merchant

### Fee Structures
Available fee structures (set by Wave after review):
- `one_percent`: 1.00% fee
- `one_fifty_bps`: 1.50% fee

### Using Aggregated Merchants
Once created, use the `aggregated_merchant_id` in:
- Checkout API: Include in checkout session creation
- Payout API: Include in payout requests

### Merchant Locking
- Wave reviews and locks merchants after approval
- Locked merchants cannot be updated (but can be deleted)
- Prevents changes to fee structures and key details

---

## Support
Contact Wave API support for:
- API key access requests
- Integration assistance
- Account limit increases
- Aggregated merchant access (for aggregators)
- Technical issues