import pyAgrum as gum
import sys
import re, csv
import argparse
import pyAgrum.lib.image as gumimage

if __name__ =="__main__":
    # get the first parameter passed to the script
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument("--input", type=str, help="input file")
    parser.add_argument("--output", type=str, help="output path")
    args = parser.parse_args()
    file_path = sys.argv[0]
    with open(args.input, "r") as fd:
        lines = fd.readlines()
        data = []
        for line in lines:
            (storeId, brandId, sectionId, productId) = re.findall("/sale/(\d+).*brandId\=(\d).*sectionId\=(\d).*productId=(\d)", line)[0]
            data += [[int(storeId), int(brandId), int(sectionId), int(productId)]]

        with open(f"{args.output}/data_generator/parsed_data.csv", "w") as fd2:
            csv_writer = csv.writer(fd2)
            csv_writer.writerow(["storeId", "brandId", "sectionId", "productId"])
            csv_writer.writerows(data)
        

    model_for_parameters = gum.BNLearner(f"{args.output}/data_generator/parsed_data.csv")
    learned_model_fp = model_for_parameters.learnBN() # learn the parameters
    learner = gum.BNLearner(f"{args.output}/data_generator/parsed_data.csv", learned_model_fp) # we will use this to learn the structure
    learner.useGreedyHillClimbing()
    # now, we set the knowledge that we know
    learner.addMandatoryArc("brandId", "storeId")  # every store belongs to a brand
    learner.addMandatoryArc("brandId", "sectionId") # some brands sells x types of products, some others not
    # and let's suppose we don't have more information on that
    new_bn = learner.learnBN()
    new_bn.saveBIF(f"{args.output}/data_generator/model.bif")
    # gumimage.export(new_bn,f"{args.output}/data_generator/model.png") # don't know why it's not working, have to check it, looks like a dependency problem
    
    # sample a new data set with more 100k rows
    generator=gum.BNDatabaseGenerator(new_bn)
    generator.setRandomVarOrder()
    generator.drawSamples(100000)
    generator.toCSV("sample_100K.csv")