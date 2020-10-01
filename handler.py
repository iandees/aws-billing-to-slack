from collections import defaultdict
import boto3
import datetime
import os
import requests
import sys

n_days = 7
today = datetime.datetime.today()
week_ago = today - datetime.timedelta(days=n_days)

sparks = ['▁', '▂', '▃', '▄', '▅', '▆', '▇'] # Leaving out the full block because Slack doesn't like it: '█'

def sparkline(datapoints):
    lower = min(datapoints)
    upper = max(datapoints)
    width = upper - lower
    n_sparks = len(sparks) - 1

    line = ""
    for dp in datapoints:
        scaled = 1 if width == 0 else (dp - lower) / width
        which_spark = int(scaled * n_sparks)
        line += (sparks[which_spark])

    return line

def delta(costs):
    return ' (%+6.2f' % (((costs[-1] - costs[-2])/costs[-2]) * 100.0 ) + '%)'

def report_cost(event, context):

    # Get account alias
    iam = boto3.client('iam')
    paginator = iam.get_paginator('list_account_aliases')
    account_name = '[NOT FOUND]'
    for aliases in paginator.paginate(PaginationConfig={'MaxItems': 1}):
        account_name = aliases['AccountAliases'][0]

    client = boto3.client('ce')

    query = {
        "TimePeriod": {
            "Start": week_ago.strftime('%Y-%m-%d'),
            "End": today.strftime('%Y-%m-%d'),
        },
        "Granularity": "DAILY",
        "Filter": {
            "Not": {
                "Dimensions": {
                    "Key": "RECORD_TYPE",
                    "Values": [
                        "Credit",
                        "Refund",
                        "Upfront",
                        "Support",
                    ]
                }
            }
        },
        "Metrics": ["UnblendedCost"],
        "GroupBy": [
            {
                "Type": "DIMENSION",
                "Key": "SERVICE",
            },
        ],
    }

    result = client.get_cost_and_usage(**query)

    buffer = "%-40s %-7s  %7s     ∆%%\n" % ("Service", "Last 7d", "$ Yday")

    cost_per_day_by_service = defaultdict(list)

    # Build a map of service -> array of daily costs for the time frame
    for day in result['ResultsByTime']:
        for group in day['Groups']:
            key = group['Keys'][0]
            cost = float(group['Metrics']['UnblendedCost']['Amount'])
            cost_per_day_by_service[key].append(cost)

    # Sort the map by yesterday's cost
    most_expensive_yesterday = sorted(cost_per_day_by_service.items(), key=lambda i: i[1][-1], reverse=True)

    for service_name, costs in most_expensive_yesterday[:5]:
        buffer += "%-40s %s $%7.2f" % (service_name, sparkline(costs), costs[-1]) + delta(costs) + "\n"

    other_costs = [0.0] * n_days
    for service_name, costs in most_expensive_yesterday[5:]:
        for i, cost in enumerate(costs):
            other_costs[i] += cost

    buffer += "%-40s %s $%7.2f" % ("Other", sparkline(other_costs), other_costs[-1]) + delta(other_costs) + "\n" 

    total_costs = [0.0] * n_days
    for day_number in range(n_days):
        for service_name, costs in most_expensive_yesterday:
            try:
                total_costs[day_number] += costs[day_number]
            except IndexError:
                total_costs[day_number] += 0.0


    buffer += "%-40s %s $%7.2f" % ("Total", sparkline(total_costs), total_costs[-1]) + delta(total_costs) + "\n" 

    credits_expire_date = os.environ.get('CREDITS_EXPIRE_DATE')
    if credits_expire_date:
        credits_expire_date = datetime.datetime.strptime(credits_expire_date, "%m/%d/%Y")

        credits_remaining_as_of = os.environ.get('CREDITS_REMAINING_AS_OF')
        credits_remaining_as_of = datetime.datetime.strptime(credits_remaining_as_of, "%m/%d/%Y")

        credits_remaining = float(os.environ.get('CREDITS_REMAINING'))

        days_left_on_credits = (credits_expire_date - credits_remaining_as_of).days
        allowed_credits_per_day = credits_remaining / days_left_on_credits

        relative_to_budget = (total_costs[-1] / allowed_credits_per_day) * 100.0

        if relative_to_budget < 60:
            emoji = ":white_check_mark:"
        elif relative_to_budget > 110:
            emoji = ":rotating_light:"
        else:
            emoji = ":warning:"

        summary = "%s Yesterday's cost for account " + account_name + " of $%5.2f is %.0f%% of credit budget $%5.2f for the day." % (
            emoji,
            total_costs[-1],
            relative_to_budget,
            allowed_credits_per_day,
        )
    else:
        summary = "Yesterday's cost for account " + account_name + " was $%5.2f" % (total_costs[-1])

    hook_url = os.environ.get('SLACK_WEBHOOK_URL')
    if hook_url:
        resp = requests.post(
            hook_url,
            json={
                "text": summary + "\n\n```\n" + buffer + "\n```",
            }
        )

        if resp.status_code != 200:
            print("HTTP %s: %s" % (resp.status_code, resp.text))
    else:
        print(summary)
        print(buffer)
