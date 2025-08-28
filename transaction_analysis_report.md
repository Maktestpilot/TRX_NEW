# Mastercard Transaction Analysis Report
## VAN Mode Analysis - Apollone | Likwid | Mastercard

### Executive Summary
This analysis examines 101 failed Mastercard transactions from the Apollone payment gateway, revealing critical patterns that require immediate attention for fraud detection and risk management.

### Dataset Overview
- **Total Transactions**: 101
- **Time Period**: August 26, 2025 (08:33 - 14:45 UTC)
- **Currency**: EUR (Euro)
- **Payment Gateway**: Sends | Mastercard | 1701
- **MCC Code**: 5817 (Digital Goods)
- **Total Transaction Value**: €2,847.59

### Critical Findings

#### 1. **100% Failure Rate - Client Verification Unsuccessful**
- **Status**: All 101 transactions failed with "Client verification unsuccessful"
- **Gateway Code**: 37 (consistent across all transactions)
- **Risk Level**: CRITICAL

#### 2. **Geographic Risk Patterns**
- **High-Risk Countries**: Romania (RO), Italy (IT), Spain (ES), United Kingdom (GB)
- **Suspicious Patterns**: Multiple transactions from same IP addresses
- **Geographic Mismatch**: Billing addresses vs. IP locations show inconsistencies

#### 3. **Card Network Analysis**
- **Issuer Banks**: Multiple Romanian banks (Banca Transilvania, BNL)
- **BIN Patterns**: 5374, 5528, 5356, 5299 series
- **Card Types**: Mix of DEBIT and CREDIT cards

#### 4. **Behavioral Red Flags**
- **Rapid Succession**: Multiple transactions within minutes
- **Amount Patterns**: €4.70, €19.78, €20.00, €24.20, €50.00, €968.00
- **User Agent Patterns**: Consistent mobile device usage
- **Time Zone Mismatches**: UTC-120 to UTC-180 discrepancies

### Fraud Detection Indicators

#### High-Risk Patterns Identified:
1. **Card Testing**: Small amounts (€4.70, €19.78) followed by larger amounts
2. **Velocity**: Multiple transactions per user within short timeframes
3. **Device Fingerprinting**: Similar browser configurations across different users
4. **IP Geolocation**: Mismatches between billing addresses and IP locations
5. **Email Patterns**: Generic email addresses with suspicious naming conventions

#### Specific Suspicious Cases:
- **User**: MIKOLAJ ANDRZEJ LUKASIK
  - Multiple transactions: €4.70 (2x), €19.78
  - IP: 31.0.95.177 (Poland)
  - Billing: Romania
  
- **User**: TABAKU ZMIRAN
  - Multiple transactions: €50.00 (2x)
  - IP: 2.37.164.197 (Italy)
  - Billing: Italy

### Risk Assessment Matrix

| Risk Factor | Score | Impact |
|-------------|-------|---------|
| Failure Rate | 10/10 | CRITICAL |
| Geographic Mismatch | 8/10 | HIGH |
| Velocity Patterns | 9/10 | HIGH |
| Card Testing | 9/10 | HIGH |
| Device Fingerprinting | 7/10 | MEDIUM-HIGH |

**Overall Risk Score: 8.6/10 (CRITICAL)**

### Immediate Action Items

#### 1. **Gateway Security Review**
- Investigate why ALL transactions are failing verification
- Review fraud detection rules and thresholds
- Check for potential gateway compromise

#### 2. **Enhanced Monitoring**
- Implement real-time velocity checks
- Add geographic risk scoring
- Monitor for card testing patterns

#### 3. **Fraud Prevention Measures**
- Block transactions from high-risk BIN ranges
- Implement stricter verification for digital goods
- Add device fingerprinting validation

### Technical Recommendations

#### SQL Queries for Monitoring:
```sql
-- High-velocity users
SELECT user_email, COUNT(*) as tx_count, 
       SUM(amount) as total_amount,
       MIN(created_at) as first_tx,
       MAX(created_at) as last_tx
FROM transactions 
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY user_email 
HAVING COUNT(*) > 3;

-- Geographic mismatches
SELECT t.user_email, t.billing_country, t.ip_country,
       COUNT(*) as mismatch_count
FROM transactions t
WHERE t.billing_country != t.ip_country
GROUP BY t.user_email, t.billing_country, t.ip_country;

-- Card testing patterns
SELECT user_email, 
       STRING_AGG(amount::text, ', ' ORDER BY created_at) as amount_sequence
FROM transactions 
WHERE user_email IN (
    SELECT user_email 
    FROM transactions 
    WHERE amount IN (470, 1978, 1979)
    GROUP BY user_email 
    HAVING COUNT(*) > 1
)
GROUP BY user_email;
```

#### Python Analysis Script:
```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def analyze_transactions(df):
    # Risk scoring
    df['risk_score'] = 0
    
    # Velocity risk
    df['velocity_risk'] = df.groupby('user_email')['id'].transform('count')
    df.loc[df['velocity_risk'] > 2, 'risk_score'] += 3
    
    # Amount risk
    df.loc[df['amount'].isin([470, 1978, 1979]), 'risk_score'] += 2
    
    # Geographic risk
    df.loc[df['billing_country'] != df['ip_country'], 'risk_score'] += 2
    
    return df

def generate_risk_report(df):
    high_risk = df[df['risk_score'] >= 5]
    return high_risk[['user_email', 'amount', 'billing_country', 'ip_country', 'risk_score']]
```

### Next Steps

#### Phase 1 (Immediate - 24 hours):
1. Block all transactions from identified high-risk BINs
2. Implement emergency velocity limits
3. Review gateway security logs

#### Phase 2 (Short-term - 1 week):
1. Deploy enhanced fraud detection rules
2. Implement device fingerprinting
3. Add geographic risk scoring

#### Phase 3 (Medium-term - 1 month):
1. Machine learning model deployment
2. Advanced behavioral analytics
3. Cross-channel fraud detection

### Conclusion
This dataset reveals a critical security situation requiring immediate intervention. The 100% failure rate combined with multiple fraud indicators suggests either a compromised gateway or sophisticated fraud ring activity. Immediate action is required to prevent financial losses and protect the payment infrastructure.

**Recommendation**: Implement emergency fraud controls and conduct comprehensive security audit of the payment gateway.

---
*Report generated by AI Data Scientist in VAN Mode*
*Date: August 26, 2025*
*Risk Level: CRITICAL*
