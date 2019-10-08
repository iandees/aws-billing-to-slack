# AWS Billing to Slack

Sends daily breakdowns of AWS costs to a Slack channel.

# Install

1. Install [`serverless`](https://serverless.com/), which I use to configure the AWS Lambda function that runs daily.

    ```
    npm install -g serverless
    npm install
    ```

1. Create an [incoming webhook](https://www.slack.com/apps/A0F7XDUAZ-incoming-webhooks) that will post to the channel of your choice on your Slack workspace. Grab the URL for use in the next step.

1. Deploy the system into your AWS account, replacing the webhook URL below with the one you generated above.

    ```
    serverless deploy --slack_url="https://hooks.slack.com/services/xxx/yyy/zzzz"
    ```

    You can also run it once to verify that it works:

    ```
    serverless invoke --function report_cost --slack_url="https://hooks.slack.com/services/xxx/yyy/zzzz"
    ```
