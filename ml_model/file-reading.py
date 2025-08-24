# Imports
import json


def main():
    file_path = "ml_model/data/products.txt"
    with open(file=file_path, mode="r", encoding="utf-8") as f:
        product_details = json.load(f)

    print(len(product_details))


if __name__ == "__main__":
    main()
