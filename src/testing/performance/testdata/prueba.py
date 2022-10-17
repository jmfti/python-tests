import argparse

if __name__ =="__main__":
    # get the first parameter passed to the script
    parser = argparse.ArgumentParser(description='sdgfsdgfsdgfsgdf.')
    parser.add_argument("--input", type=str, help="input file")
    parser.add_argument("--output", type=str, help="output path")
    args = parser.parse_args()
    
    print(args.input)
    
    print(args.output)