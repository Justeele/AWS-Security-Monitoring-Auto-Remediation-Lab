# AWS Security Monitoring & Auto-Remediation Lab

This is a hands-on lab I built to get real experience with AWS security tooling beyond just reading about it. It covers the full chain — centralized logging, alerting, threat detection, and automated remediation — built first in the console so I actually understood each piece, then being ported over to Terraform.

## Why I built this

A lot of "AWS security" projects on GitHub stop at "enabled CloudTrail and GuardDuty, here's a screenshot." I wanted something that actually closes the loop — detection leads to a response, not just a notification nobody reads. So the centerpiece here is a Lambda that gets triggered by specific GuardDuty findings and quarantines the affected instance automatically.

## How it's wired together

```
                                   CloudTrail
                              (multi-region, log validation on)
                                       |
                  ----------------------------------------
                  |                                        |
                  v                                        v
            S3 (hardened)                          CloudWatch Logs
       - Block Public Access: ON                  - Metric filters:
       - Default encryption: ON                       Root usage
                                                        IAM policy changes
                                                        SG changes
                                                            |
                                                            v
                                                   CloudWatch Alarms
                                                            |
                                                            v
                                                    SNS (email alerts)


            GuardDuty
        (threat detection)
                |
                v
           EventBridge
   Rule 1: all findings --> SNS (just for visibility)
   Rule 2: specific finding types --> Lambda
                |                          |
                v                          v
               SNS                      Lambda
        (all findings)          - pulls instance ID from finding
                                 - swaps its SG to quarantine-sg
                                 - logs the outcome to CloudWatch
```

## What's actually in here

- **CloudTrail** — multi-region trail, log file validation on, logging into a locked-down S3 bucket
- **S3** — went in and manually confirmed Block Public Access and encryption were on instead of just trusting the defaults AWS sets when it creates the bucket
- **CloudWatch metric filters** — three of them: root account usage, IAM policy changes, security group changes. These line up with stuff auditors actually check (CIS Benchmark territory)
- **CloudWatch alarms** — one per filter, all pointed at the same SNS topic
- **GuardDuty** — turned on, tested against both sample findings and a real EC2 instance
- **EventBridge** — two rules. One's broad and just forwards every GuardDuty finding to SNS so a human can see it. The other is scoped to three specific finding types and triggers the Lambda
- **Lambda** — grabs the instance ID out of the finding and swaps its security group to an isolated one with no inbound or outbound rules, basically cutting it off from the network

## A few decisions I made on purpose (and would explain if asked)

**Scoped the auto-remediation instead of letting it fire on everything.** GuardDuty has 50+ finding types and a lot of them are low-severity or informational. I didn't want a sample/test finding — or a low-confidence real one — automatically yanking a legitimate instance offline. So the Lambda only fires on three high-confidence finding types (SSH brute force, RDP brute force, and a C&C/backdoor indicator). Everything else still goes to SNS so someone can look at it, it just doesn't trigger an automatic response.

**Verified the S3 bucket settings instead of assuming.** AWS does a decent job setting sane defaults when CloudTrail auto-creates the logging bucket, but I went and actually checked Block Public Access and encryption rather than taking that on faith.

**Left the IAM policy on the Lambda broader than I'd want in production.** Right now `ec2:ModifyInstanceAttribute` is scoped to `Resource: "*"`. In a real environment I'd tighten this to specific instance ARNs or a tag-based condition. Leaving it as-is for the lab, but it's a known gap, not an oversight.

**Set default values of 0 on the metric filters.** Small thing, but if you don't do this, CloudWatch can't evaluate an alarm for a metric that's never had a matching event — it just sits in INSUFFICIENT_DATA forever instead of OK. Easy to miss.

## How I tested this (not just deployed and walked away)

- Made a real IAM policy change and confirmed the alarm fired and the email actually showed up
- Did the same with a security group change
- Generated GuardDuty's sample findings and watched them flow through EventBridge to SNS
- Manually invoked the Lambda with a fake instance ID first, just to confirm the code parsed the event correctly before testing against anything real
- Spun up a free-tier EC2 instance, triggered the remediation, and confirmed in the console that its security group actually got swapped to the quarantine SG
- Regenerated the sample findings again and confirmed EventBridge correctly filtered down to only the three finding types I scoped it to, and that each one triggered the Lambda on its own without me doing anything manually

## Repo layout

```
.
├── README.md
├── terraform/              # IaC version, in progress
│   ├── cloudtrail.tf
│   ├── s3.tf
│   ├── cloudwatch.tf
│   ├── guardduty.tf
│   ├── eventbridge.tf
│   ├── lambda.tf
│   └── iam.tf
├── lambda/
│   └── remediation/
│       └── lambda_function.py
└── docs/
    └── screenshots/         # account IDs redacted before posting
```

## Still to do

- Finish the Terraform rebuild of everything above
- Add severity filtering to the broad SNS rule so it's not blasting an inbox every time someone generates sample findings
- Tighten the Lambda's IAM policy with a tag condition instead of `Resource: "*"`
- Maybe pair this with a CloudGoat writeup — attack side and defense side together
