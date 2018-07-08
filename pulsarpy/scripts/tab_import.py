#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###Author
#Nathaniel Watson
#2017-09-18
#nathankw@stanford.edu
###

"""
Given a tab-delimited sheet, imports records of the specified Model into Pulsar LIMS. Array values
should be comma-delimted as this program will split on the comma and add array literals. Array
fields are only assumed when the field name has an 'ids' suffix. 
"""
import argparse

import pulsarpy.models as models
import pulsarpy.utils


def get_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-m", "--model", required=True, help="""
      The name of the model to import the records to, i.e. Biosample or CrisprModification.""")
    parser.add_argument("-i", "--infile", required=True, help="""
      The tab-delimited input file containing records (1 per row). There must be a field-header line
      as the first row, and field names must match record attribute names. Any field names that start
      with a '#' will be skipped. Any rows that start with a '#' will also be skipped (apart from the
      header line).""")
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()
    infile = args.infile
    model = getattr(models, args.model)
    fh = open(infile)
    header = fh.readline().strip("\n").split("\t")
    field_positions = [header.index(x) for x in header if not x.startswith("#") and x.strip()]
    line_cnt = 1 # Already read header line
    for line in fh:
        line_cnt += 1
        if line.startswith("#"):
            continue
        payload = {}
        line = line.strip("\n").split("\t")
        for pos in field_positions:
            val = line[pos].strip()
            if not val:
               continue
            field_name = header[pos]
            if field_name.endswith("ids"):
                # An array field (i.e. pooled_from_ids). Split on comma and convert to list:
                val = [x.strip() for x in val.split(",")]
            payload[header[pos]] = val
        print("Submitting line {}".format(line_cnt))
        res = model.post(payload)
        print("Success: ID {}".format(res["id"]))

if __name__ == "__main__":
    main()

