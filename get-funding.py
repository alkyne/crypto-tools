import requests
import time
from datetime import datetime, timedelta, timezone
import sys

# Constants
API_URL = "https://api.hyperliquid.xyz/info"
HEADERS = {
    "Content-Type": "application/json"
}
# COIN = "PENGU"
# COIN = "HYPE"
COIN = sys.argv[1].upper()
REQUEST_TYPE = "fundingHistory"

# Define the time interval for each request (e.g., 30 days)
INTERVAL_DAYS = 30

def get_current_time_ms():
    """Returns the current time in milliseconds."""
    return int(time.time() * 1000)

def get_time_range(start_ms, end_ms):
    """Generates a list of (start, end) tuples representing time ranges."""
    ranges = []
    current_start = start_ms
    interval_ms = INTERVAL_DAYS * 24 * 60 * 60 * 1000  # Convert days to milliseconds

    while current_start < end_ms:
        current_end = current_start + interval_ms
        if current_end > end_ms:
            current_end = end_ms
        ranges.append((current_start, current_end))
        current_start = current_end + 1  # Avoid overlap

    return ranges

def fetch_funding_history(coin, start_time, end_time=None):
    """
    Fetches funding history for a given coin within the specified time range.

    :param coin: The base cryptocurrency (e.g., 'PENGU')
    :param start_time: Start time in milliseconds (inclusive)
    :param end_time: End time in milliseconds (inclusive). Defaults to current time if None.
    :return: List of funding rate records
    """
    if end_time is None:
        end_time = get_current_time_ms()

    payload = {
        "type": REQUEST_TYPE,
        "coin": coin,
        "startTime": start_time,
        "endTime": end_time
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        # **Adjust the following line based on the actual API response structure**
        # Assuming the funding rates are under the key 'fundingRates'
        # funding_rates = data.get("fundingRates", [])
        return data

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} - Response: {response.text}")
    except Exception as err:
        print(f"An error occurred: {err}")

    return []

def print_funding_rates(funding_rates):
    """
    Prints the funding rates in a readable format.

    :param funding_rates: List of funding rate records
    """
    if not funding_rates:
        print("No funding rates found for the specified time range.")
        return

    print(f"Historical Funding Rates for {COIN}-USD:")
    print("-" * 60)
    print(f"{'Timestamp':<30} {'Funding Rate (%)':<20} {"APR (%)":<20}")
    print("-" * 60)

    for rate in funding_rates:
        # **Adjust the keys based on the actual API response**
        timestamp_ms = rate.get("time")  # Assuming timestamp is in milliseconds
        funding_rate = rate.get("fundingRate")  # Assuming funding rate is under 'fundingRate'
        funding_rate = float(funding_rate) * 100 
        funding_rate_apr = funding_rate * 24 * 365

        # Convert timestamp to readable format
        if timestamp_ms:
            try:
                # timestamp = datetime.utcfromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S UTC+9')
            except Exception:
                timestamp = "Invalid Timestamp"
        else:
            timestamp = "N/A"

        print(f"{timestamp:<30} {funding_rate:<20.4f} {funding_rate_apr:<20.4f}")

    n = 48 # last n hours
    last_n_rates = funding_rates[-n:]
    valid_rates = []
    for rate in last_n_rates:
        funding_rate = rate.get("fundingRate")
        if isinstance(funding_rate, (int, float)):
            valid_rates.append(funding_rate)
        else:
            try:
                valid_rates.append(float(funding_rate))
            except (TypeError, ValueError):
                print(f"Invalid funding rate value encountered: {funding_rate}%")

    average = sum(valid_rates) / len(valid_rates)
    average *= 100 * 24 * 365 # to APR
    print(f"\nAverage of the last {n} funding rates: {average:.1f}%")

    n = 24
    last_n_rates = funding_rates[-n:]
    valid_rates = []
    for rate in last_n_rates:
        funding_rate = rate.get("fundingRate")
        if isinstance(funding_rate, (int, float)):
            valid_rates.append(funding_rate)
        else:
            try:
                valid_rates.append(float(funding_rate))
            except (TypeError, ValueError):
                print(f"Invalid funding rate value encountered: {funding_rate}%")
    average = sum(valid_rates) / len(valid_rates)
    average *= 100 * 24 * 365 # to APR
    print(f"Average of the last {n} funding rates: {average:.1f}%")


def save_funding_rates_to_file(funding_rates, filename=f"funding_history_{COIN}.csv"):
    """
    Saves the funding rates to a CSV file.

    :param funding_rates: List of funding rate records
    :param filename: Name of the CSV file to save data
    """
    import csv

    if not funding_rates:
        print("No data to save.")
        return

    # **Adjust the keys based on the actual API response**
    fieldnames = funding_rates[0].keys()

    try:
        with open(filename, mode='w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(funding_rates)
        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"Failed to save data to file: {e}")

def main():
    # Define the overall time range for historical data
    # Example: Fetch data from January 1, 2020 to now
    # Adjust the start date as per the earliest available data
    
    # start_date = datetime(2024, 12, 28)
    # start_time_ms = int(start_date.timestamp() * 1000)
    start_time_ms = get_current_time_ms() - 52 * 60 * 60 * 1000 # 52 hours before
    end_time_ms = get_current_time_ms()

    # Generate time ranges
    time_ranges = get_time_range(start_time_ms, end_time_ms)
    print(f"Total requests to be made: {len(time_ranges)}")

    all_funding_rates = []

    for idx, (start_ms, end_ms) in enumerate(time_ranges):
        # print(f"Fetching data {idx + 1}/{len(time_ranges)}: {datetime.utcfromtimestamp(start_ms / 1000).strftime('%Y-%m-%d')} to {datetime.utcfromtimestamp(end_ms / 1000).strftime('%Y-%m-%d')}")
        print(
            f"Fetching data {idx + 1}/{len(time_ranges)}: "
            f"{datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d')} "
            f"to {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d')}"
        )
        funding_rates = fetch_funding_history(COIN, start_ms, end_ms)
        all_funding_rates.extend(funding_rates)

        # Respectful delay to avoid overwhelming the API
        time.sleep(0.5)  # 500 milliseconds; adjust as per API rate limits

    # Remove potential duplicates based on timestamp
    unique_funding_rates = {rate["time"]: rate for rate in all_funding_rates}.values()

    # Sort the funding rates by timestamp
    sorted_funding_rates = sorted(unique_funding_rates, key=lambda x: x.get("time", 0))

    # Print the funding rates
    print_funding_rates(sorted_funding_rates)

    # Optionally, save to a CSV file
    # save_funding_rates_to_file(sorted_funding_rates)
    print (f"Crypto: {COIN}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
        sys.exit(0)