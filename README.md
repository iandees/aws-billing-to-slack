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
    serverless deploy --stage="prod" --slack_url="https://hooks.slack.com/services/xxx/yyy/zzzz"
    ```

    You can also run it once to verify that it works:

    ```
    serverless invoke --function report_cost --slack_url="https://hooks.slack.com/services/xxx/yyy/zzzz"
    ```

## Support for AWS Credits

If you have AWS credits on your account and want to see them taken into account on this report, head to [your billing dashboard](https://console.aws.amazon.com/billing/home?#/credits) and note down the "Expiration Date", "Amount Remaining", and the "as of" date towards the bottom of the page. Add all three of these items to the command line when executing the `deploy` or `invoke`:

    ```
    serverless deploy \
        --slack_url="https://hooks.slack.com/services/xxx/yyy/zzzz" \
        --credits_expire_date="mm/dd/yyyy" \
        --credits_remaining_date="mm/dd/yyyy" \
        --credits_remaining="xxx.xx"
    ```

## Other Useful CLI Arguments Related to your AWS account

With none of the folling arguments passed (--aws_account, --aws_profile, --aws_region), sensible defaults are attempted to be retrieved. For example, boto3 is used to try and determine your AWS account alias if it exists, and if not your AWS account ID. Additionally, for your AWS profile the environment variable AWS_PROFILE is read and used if present, otherwise fallback to 'default'. Finally, for your AWS region the environment variables AWS_REGION, then AWS_DEFAULT_REGION are read and used if present, otherwise fallback to 'us-east-1' (N. Virginia). However, if you supply one of these arguments when executing the `deploy` or `invoke` command, then these values are taken and no defaults are attempted to be retrieved:

    ```
    serverless deploy \
        --slack_url="https://hooks.slack.com/services/xxx/yyy/zzzz" \
        --aws_account="my custom account name" \
        --aws_profile="default" \
        --aws_region="eu-west-1"
    ```

## Authors

- [Alex Ley](https://github.com/Alex-ley)
- [Enrico Stahn](https://github.com/estahn)
- [Ian Dees](https://github.com/iandees)
- [Regis Wilson](https://github.com/rwilson-release)
- [Rui Pinho](https://github.com/ruiseek)
- [Tamas Flamich](https://github.com/tamasflamich)
