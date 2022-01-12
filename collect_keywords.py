import argparse
import itertools
import json
import os
import shutil
import tqdm

import zstd


class Preprocessor(object):
    def __init__(self):
        pass

    def process(self, text):
        return text.lower().strip()


class PrefixKeywordsCollector(object):
    def __init__(self, keywords, lcontext=1, rcontext=0):
        self.preprocessor = Preprocessor()
        self.keywords = self._prepare_keywords(keywords)
        self.lcontext = lcontext
        self.rcontext = rcontext

    def _prepare_keywords(self, keywords):
        keywords = [self.preprocessor.process(key) for key in keywords]
        return list(sorted(keywords, key=lambda x: -len(x)))

    def _prepare_lines(self, lines):
        return [self.preprocessor.process(line) for line in lines]

    def _prefix_match(self, text):
        for key in self.keywords:
        # return longest keywords match
            if text.startswith(key):
                return key
        return None

    def collect(self, lines):
        result = {key: [] for key in self.keywords}
        lines = self._prepare_lines(lines)
        lines = [''] * self.lcontext + lines + [''] * self.rcontext
        for i, line in tqdm.tqdm(enumerate(lines), total=len(lines)):
            match = self._prefix_match(line)
            if match is not None:
                result[match].append(lines[i - self.lcontext: i + self.rcontext + 1])
        return result


def load_lines(zst_json):
    with open(zst_json, 'rb') as fin:
        bytes_data = zstd.decompress(fin.read())
    json_data = json.loads(bytes_data)
    lines = []
    for text in tqdm.tqdm(json_data):
        text_lines = [item.strip() for item in text.split('"') if item.strip() != '']
        lines.extend(text_lines)
    return lines


def load_keywords(txt_file):
    with open(txt_file, 'r') as fin:
        keywords = fin.readlines()
    keywords = [keyword.strip() for keyword in keywords]
    return keywords


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_dir', '-d', default='out')
    parser.add_argument('--output_dir', '-o', default='keywords_found')
    parser.add_argument('--keywords_file', '-k', required=True)
    args = parser.parse_args()

    assert os.path.isdir(args.data_dir), f'Could not find data dir {args.data_dir}'
    assert os.path.isfile(args.keywords_file), f'Could not find keywords file'
    if os.path.exists(args.output_dir):
        print(f'Removing output dir {args.output_dir}...')
        shutil.rmtree(args.output_dir)
    os.mkdir(args.output_dir)

    print('Loading keywords...')
    keywords = load_keywords(args.keywords_file)
    keywords_collector = PrefixKeywordsCollector(keywords)

    for data_file in os.listdir(args.data_dir):
        print(f'Loading {data_file}...')
        lines = load_lines(os.path.join(args.data_dir, data_file))
        print(f'Collecting keywords for {data_file}...')
        collected = keywords_collector.collect(lines)
        out_name = data_file.split('.')[0] + '_keywords.json'
        with open(os.path.join(args.output_dir, out_name), 'w') as fout:
            json.dump(collected, fout, sort_keys=True, indent=4)