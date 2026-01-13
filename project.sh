#!/usr/bin/env bash

OUT_DIR="."

#code2logic "$OUT_DIR/" -f yaml -o "$OUT_DIR/project.yaml" --compact --with-schema
#code2logic "$OUT_DIR/" -f hybrid -o "$OUT_DIR/project.hybrid.yaml" --with-schema
code2logic "$OUT_DIR/" -f toon -o "$OUT_DIR/project.toon" --function-logic --with-schema
#code2logic ./ -f toon -o project.toon --function-logic --with-schema
