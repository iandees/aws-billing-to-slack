from collections import defaultdict
import boto3
import datetime
import os
import requests
import sys

n_days = 7
yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
week_ago = yesterday - datetime.timedelta(days=n_days)

# It seems that the sparkline symbols don't line up (probalby based on font?) so put them last
# Also, leaving out the full block because Slack doesn't like it: '█'
sparks = ['▁', '▂', '▃', '▄', '▅', '▆', '▇']

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
    if (len(costs) > 1 and costs[-1] >= 1 and costs[-2] >= 1):
        # This only handles positive numbers
        result = ((costs[-1]/costs[-2])-1)*100.0
    else:
        result = 0
    return result

def report_cost(event, context, result: dict = None, yesterday: str = None, new_method=True):

    if yesterday is None:
        yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
    else:
        yesterday = datetime.datetime.strptime(yesterday, '%Y-%m-%d')

    week_ago = yesterday - datetime.timedelta(days=n_days)
    # Generate list of dates, so that even if our data is sparse,
    # we have the correct length lists of costs (len is n_days)
    list_of_dates = [
        (week_ago + datetime.timedelta(days=x)).strftime('%Y-%m-%d')
        for x in range(n_days)
    ]
    print(list_of_dates)

    # Get account account name from env, or account id/account alias from boto3
    account_name = os.environ.get("AWS_ACCOUNT_NAME", None)
    if account_name is None:
        iam = boto3.client("iam")
        paginator = iam.get_paginator("list_account_aliases")
        for aliases in paginator.paginate(PaginationConfig={"MaxItems": 1}):
            if "AccountAliases" in aliases and len(aliases["AccountAliases"]) > 0:
                account_name = aliases["AccountAliases"][0]

    if account_name is None:
        account_name = boto3.client("sts").get_caller_identity().get("Account")

    if account_name is None:
        account_name = "[NOT FOUND]"

    client = boto3.client('ce')

    query = {
        "TimePeriod": {
            "Start": week_ago.strftime('%Y-%m-%d'),
            "End": yesterday.strftime('%Y-%m-%d'),
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

    # Only run the query when on lambda, not when testing locally with example json
    if result is None:
        result = client.get_cost_and_usage(**query)

    cost_per_day_by_service = defaultdict(list)

    if new_method == False:
        # Build a map of service -> array of daily costs for the time frame
        for day in result['ResultsByTime']:
            for group in day['Groups']:
                key = group['Keys'][0]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                cost_per_day_by_service[key].append(cost)
    else:
        # New method, which first creates a dict of dicts
        # then loop over the services and loop over the list_of_dates
        # and this means even for sparse data we get a full list of costs
        cost_per_day_dict = defaultdict(dict)

        for day in result['ResultsByTime']:
            start_date = day["TimePeriod"]["Start"]
            for group in day['Groups']:
                key = group['Keys'][0]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                cost_per_day_dict[key][start_date] = cost

        for key in cost_per_day_dict.keys():
            for start_date in list_of_dates:
                cost = cost_per_day_dict[key].get(start_date, 0.0) # fallback for sparse data
                cost_per_day_by_service[key].append(cost)

    # Sort the map by yesterday's cost
    most_expensive_yesterday = sorted(cost_per_day_by_service.items(), key=lambda i: i[1][-1], reverse=True)

    service_names = [k for k,_ in most_expensive_yesterday[:5]]
    longest_name_len = len(max(service_names, key = len))

    buffer = f"{'Service':{longest_name_len}} ${'Yday':8} {'∆%':>5} {'Last 7d':7}\n"

    for service_name, costs in most_expensive_yesterday[:5]:
        buffer += f"{service_name:{longest_name_len}} ${costs[-1]:8,.2f} {delta(costs):4.0f}% {sparkline(costs):7}\n"

    other_costs = [0.0] * n_days
    for service_name, costs in most_expensive_yesterday[5:]:
        for i, cost in enumerate(costs):
            other_costs[i] += cost

    buffer += f"{'Other':{longest_name_len}} ${other_costs[-1]:8,.2f} {delta(other_costs):4.0f}% {sparkline(other_costs):7}\n"

    total_costs = [0.0] * n_days
    for day_number in range(n_days):
        for service_name, costs in most_expensive_yesterday:
            try:
                total_costs[day_number] += costs[day_number]
            except IndexError:
                total_costs[day_number] += 0.0

    buffer += f"{'Total':{longest_name_len}} ${total_costs[-1]:8,.2f} {delta(total_costs):4.0f}% {sparkline(total_costs):7}\n"

    cost_per_day_by_service["total"] = total_costs[-1]

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

        summary = (f"{emoji} Yesterday's cost for {account_name} ${total_costs[-1]:,.2f} "
                   f"is {relative_to_budget:.2f}% of credit budget "
                   f"${allowed_credits_per_day:,.2f} for the day."
                  )
    else:
        summary = f"Yesterday's cost for account {account_name} was ${total_costs[-1]:,.2f}"

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

    # for running locally to test output
    return cost_per_day_by_service

if __name__ == "__main__":
    # for running locally to test
    import json
    with open("example_boto3_result.json", "r") as f:
        example_result = json.load(f)
    with open("example_boto3_result2.json", "r") as f:
        example_result2 = json.load(f)

    # New Method with 2 example jsons
    cost_dict = report_cost(None, None, example_result, yesterday="2021-08-23", new_method=True)
    assert "{0:.2f}".format(cost_dict.get("total", 0.0)) == "286.37", f'{cost_dict.get("total"):,.2f} != 286.37'    
    cost_dict = report_cost(None, None, example_result2, yesterday="2021-08-29", new_method=True)
    assert "{0:.2f}".format(cost_dict.get("total", 0.0)) == "21.45", f'{cost_dict.get("total"):,.2f} != 21.45'

    # Old Method with same jsons (will fail)
    cost_dict = report_cost(None, None, example_result, yesterday="2021-08-23", new_method=False)
    assert "{0:.2f}".format(cost_dict.get("total", 0.0)) == "286.37", f'{cost_dict.get("total"):,.2f} != 286.37' 
    cost_dict = report_cost(None, None, example_result2, yesterday="2021-08-29", new_method=False)
    assert "{0:.2f}".format(cost_dict.get("total", 0.0)) == "21.45", f'{cost_dict.get("total"):,.2f} != 21.45'
