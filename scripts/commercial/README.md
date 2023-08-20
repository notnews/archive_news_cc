### Take out commercial segments

Use dataset from https://tvnews.stanford.edu/methodology#commercials to take out commercial segments

1) Download JSON file from https://tvnews.stanford.edu/export/commercial

2) Run `remove-commercial-<year>.ipynb` to parse original HTML files and take out commercial segments

3) Run `merge-nc-<year>.ipynb` to merge back the text without commercial segments (`text_nc` column) to the original dataset
