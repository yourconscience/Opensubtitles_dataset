import argparse
import json
import os
import random
import shutil
import tqdm

import pandas as pd
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
            if text.startswith(key) and (len(text) == len(key) or not(text[len(key)].isalpha())):
                return key
        return None

    def collect(self, lines):
        result = {key: [] for key in self.keywords}
        lines = self._prepare_lines(lines)
        lines = [''] * self.lcontext + lines + [''] * self.rcontext
        for i, line in tqdm.tqdm(enumerate(lines), total=len(lines)):
            match = self._prefix_match(line)
            if match is not None:
                lcontext = '\n'.join(lines[i - self.lcontext : i])
                rcontext = '\n'.join(lines[i + 1 : i + self.rcontext + 1])
                result[match].append([lcontext, line, rcontext])
        return result


class DatasetBuilder(object):
    def __init__(self, max_samples=50*1000):
        self.max_samples = max_samples
        self.data = {}

    def _filter_samples(self, samples):
        return [sample for sample in samples if len(sample[0]) > 2 and all(s.isascii() for s in sample)]

    def add_data(self, data_dict):
        for key in data_dict:
            if key not in self.data:
                self.data[key] = []
            new_samples = self._filter_samples(data_dict[key])
            if len(self.data[key]) + len(new_samples) > self.max_samples:
                self.data[key] = random.sample(self.data[key] + new_samples, self.max_samples)
            else:
                self.data[key].extend(new_samples)

    def dump_data(self, filename, test_ratio=None):
        columns = ['keyword', 'lcontext', 'line', 'rcontext']
        data_iter = ([key] + sample for key, samples in self.data.items() for sample in samples)
        df = pd.DataFrame(data_iter, columns=columns)
        if test_ratio is not None:
            assert 0.0 < test_ratio < 1.0, "Wrong test ratio value"
            df_train = df.sample(frac = 1 - test_ratio, random_state=42)
            df_test = df.drop(df_train.index)
            df_train.to_csv(filename + '_train.csv', sep='\t', index=False)
            df_test.to_csv(filename + '_test.csv', sep='\t', index=False)
        else:
            df = df.sample(frac=1, random_state=42)
            df.to_csv(filename + '.csv', sep='\t')


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
    parser.add_argument('--output_dir', '-o', default='keywords_data')
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
    dataset_builder = DatasetBuilder()

    for data_file in os.listdir(args.data_dir):
        print(f'Loading {data_file}...')
        lines = load_lines(os.path.join(args.data_dir, data_file))
        print(f'Collecting keywords for {data_file}...')
        collected = keywords_collector.collect(lines)
        dataset_builder.add_data(collected)
    
    dataset_builder.dump_data(os.path.join(args.output_dir, 'keywords'), test_ratio=0.1)