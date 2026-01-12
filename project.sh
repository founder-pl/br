#!/usr/bin/env bash

OUT_DIR="."

code2logic code2logic -f yaml -o "$OUT_DIR/project.yaml" --compact --with-schema
code2logic code2logic -f hybrid -o "$OUT_DIR/project.hybrid.yaml" --with-schema
code2logic code2logic -f toon -o "$OUT_DIR/project.toon" --function-logic --with-schema
