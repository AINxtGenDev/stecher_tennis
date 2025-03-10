#!/bin/bash
# Define the base directory and output file
BASE_DIR="/home/nuc8/05_development/02_python/01_stecher_tennis/mobile_stecher_tennis"
OUTPUT_FILE="mobile_stecher_tennis.txt"

# Clear the output file if it exists, or create it
> "$OUTPUT_FILE"

# Append pubspec.yaml content with a header
echo "===== pubspec.yaml =====" >> "$OUTPUT_FILE"
echo "File: $BASE_DIR/pubspec.yaml" >> "$OUTPUT_FILE"
cat "$BASE_DIR/pubspec.yaml" >> "$OUTPUT_FILE"
echo -e "\n\n" >> "$OUTPUT_FILE"

# Find and append all .dart files from the lib folder with headers
find "$BASE_DIR/lib" -type f -name "*.dart" | while read -r file; do
    echo "===== $(basename "$file") =====" >> "$OUTPUT_FILE"
    echo "File: $file" >> "$OUTPUT_FILE"
    cat "$file" >> "$OUTPUT_FILE"
    echo -e "\n\n" >> "$OUTPUT_FILE"
done

echo "All files have been concatenated into $OUTPUT_FILE."
