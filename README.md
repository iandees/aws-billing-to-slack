# AWS Billing to Slack

![image](https://user-images.githubusercontent.com/261584/66362145-3903a200-e947-11e9-91bd-6e40e5919ac4.png)

Sends daily breakdowns of AWS costs to a Slack channel.

# Install

1. Install [`serverless`](https://serverless.com/), which I use to configure the AWS Lambda function that runs daily.

    ```
    npm install -g serverless
    ```

1. Create an [incoming webhook](https://www.slack.com/apps/new/A0F7XDUAZ) that will post to the channel of your choice on your Slack workspace. Grab the URL for use in the next step.

1. Create the service on your local machine. cd to your directory and run this command. Replace path with the path name for the service and app name for the service.

    ```
    serverless create \
      --template-url="https://github.com/iandees/aws-billing-to-slack.git" \
      --path="app-aws-cost" \
      --name="app-aws-cost"
    ```

1. Install pipenv
   
    ```
    pip install pipenv
    ```

1. Install serverless python requirements

    ```
    serverless plugin install -n serverless-python-requirements
    ```

1. Deploy the system into your AWS account, replacing the webhook URL below with the one you generated above.

    ```
    serverless deploy --stage="prod" --param="slack_url=https://hooks.slack.com/services/xxx/yyy/zzzz"
    ```

    You can also run it once to verify that it works:

    ```
    serverless invoke --function report_cost --stage="prod" --param="slack_url=https://hooks.slack.com/services/xxx/yyy/zzzz"
    ```

## Support for AWS Credits

If you have AWS credits on your account and want to see them taken into account on this report, head to [your billing dashboard](https://console.aws.amazon.com/billing/home?#/credits) and note down the "Expiration Date", "Amount Remaining", and the "as of" date towards the bottom of the page. Add all three of these items to the command line when executing the `deploy` or `invoke`:

    ```
    serverless deploy \
        --param "slack_url=https://hooks.slack.com/services/xxx/yyy/zzzz" \
        --param "credits_expire_date=mm/dd/yyyy" \
        --param "credits_remaining_date=mm/dd/yyyy" \
        --param "credits_remaining=xxx.xx"
    ```

## Support for other Dimensions

If you have and AWS Organisation established and would like to see a breakdown by account, you can override the default dimensions with parameters: 

    ```
    serverless deploy \
        --param "slack_url=https://hooks.slack.com/services/xxx/yyy/zzzz" \
        --param "group=LINKED_ACCOUNT" \
        --param "group_length=15"
    ```

Possible value for `group` are:

* AZ
* INSTANCE_TYPE 
* LINKED_ACCOUNT 
* OPERATION
* PURCHASE_TYPE 
* SERVICE
* USAGE_TYPE 
* PLATFORM 
* TENANCY
* RECORD_TYPE
* LEGAL_ENTITY_NAME 
* INVOICING_ENTITY 
* DEPLOYMENT_OPTION 
* DATABASE_ENGINE
* CACHE_ENGINE
* INSTANCE_TYPE_FAMILY
* REGION, BILLING_ENTITY
* RESERVATION_ID
* SAVINGS_PLANS_TYPE
* SAVINGS_PLAN_ARN
* OPERATING_SYSTEM


## Other Useful CLI Arguments Related to your AWS account

By default, `AWS_PROFILE` and `AWS_REGION` are defaulting to `default` and `us-east-1`. These value can be changed by modifying the environment. For aws account, sensible default is attempted to be retrieved. For example, boto3 is used to try and determine your AWS account alias if it exists, and if not your AWS account ID. 
Additionally, for your AWS region the environment variables `AWS_REGION`, then `AWS_DEFAULT_REGION` are read and used if present, otherwise fallback to 'us-east-1' (N. Virginia).

    ```
    AWS_PROFILE="default" AWS_REGION="eu-west-1" serverless deploy \
        --param "slack_url=https://hooks.slack.com/services/xxx/yyy/zzzz" \
        --param "aws_account=my custom account name"
    ```

## Authors

- [Alex Ley](https://github.com/Alex-ley)
- [Enrico Stahn](https://github.com/estahn)
- [Ian Dees](https://github.com/iandees)
- [Regis Wilson](https://github.com/rwilson-release)
- [Rui Pinho](https://github.com/ruiseek)
- [Tamas Flamich](https://github.com/tamasflamich)
