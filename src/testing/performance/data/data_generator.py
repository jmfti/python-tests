import csv
import hashlib
import random

def main():
    people = [[f"{i}@company.com"] for i in range(1000)]
    people.insert(0, ["email"])
    # write people array to csv in unix format
    with open("people.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(people)
    
    signatures = [ [hashlib.md5(str(random.random()).encode("utf8")).hexdigest()] for i in range(1000)]
    signatures.insert(0, ["signature"])
    with open("signatures.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(signatures)

if __name__ == "__main__":
    main()