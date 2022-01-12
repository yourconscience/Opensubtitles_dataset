# Opensubtitles_dataset
downloads and parses subtitle dataset from opensubtitles.org

# Usage
python3 parse_opensubtitle_xml.py

the above will download a zip containing the english opensubtitles corpus, and extract text from all the xml files (removes metadata)

# Keywords collection
python3 collect_keywords -k $keywords_filename [-o $output_dir]

this will find all keywords occurrences in subtitles dataset with some context and stores in separate json files