# Imports
from requests import get
from bs4 import BeautifulSoup as bs

import csv


# Exports all the CPU data to the specified
# csv file
def export_to_csv(data, csv_file_name):
    print("Generating '" + csv_file_name + "'...")
    try:
        with open(
            f"ml_model/data/{csv_file_name}", "w", newline="", encoding="utf-8"
        ) as f:
            writer = csv.writer(f)
            writer.writerow(data.keys())
            writer.writerows(zip(*data.values()))
    except:
        print(
            "Error: unable to write to '"
            + csv_file_name
            + "'. Make sure you have "
            + "permission to write to this file and it is not currently open and try again"
        )


def main():
    file_names = ["cpu-data.csv", "gpu-data.csv"]
    base_urls = [
        "https://www.cpubenchmark.net/cpu_list.php",
        "https://www.videocardbenchmark.net/gpu_list.php",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"
    }

    ids = ["cpu", "gpu"]

    for i in range(len(base_urls)):
        result = get(base_urls[i], headers=headers)
        soup = bs(result.content, "lxml")
        print(soup)

        # Get the table
        table = soup.find("table", {"id": "cputable"})
        # Get rows
        rows = table.find_all("tr", {"id": lambda x: x and x.startswith(ids[i])})

        data = {"Name": [], "Score": []}
        for row in rows:
            columns = row.find_all("td")

            if len(columns) >= 2:
                data["Name"].append(columns[0].text.strip().lower())
                data["Score"].append(int(columns[1].text.strip().replace(",", "")))

        export_to_csv(data=data, csv_file_name=file_names[i])


if __name__ == "__main__":
    main()
