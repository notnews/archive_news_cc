## Download Closed Captions of News Videos from Archive.org


### Data

The data are hosted on Google Cloud Storage. It is setup such that the requestor pays. 

There are two separate datasets, one with ~ 500k and another with about 860k news transcripts.

**500k Dataset**

* [CSV](https://storage.googleapis.com/closed-caption-tv-news-archive/archive-cc-2014.csv.7z)
* [HTML](https://storage.googleapis.com/closed-caption-tv-news-archive/html-2014.7z)

**860k Dataset**

* [CSV](https://storage.googleapis.com/closed-caption-tv-news-archive/archive-cc-2017.csv.gz)
* [HTML](https://storage.googleapis.com/closed-caption-tv-news-archive/html.tar.gz)
* [Meta](https://storage.googleapis.com/closed-caption-tv-news-archive/meta.tar.gz)

### Downloading the Data from Archive.org

Download closed caption transcripts of nearly 1.3M news shows from [http://archive.org](http://archive.org). 

There are three steps to downloading the transcripts:

1. We start by searching [https://archive.org/advancedsearch.php](https://archive.org/advancedsearch.php) with collection `collection:"tvarchive"`. This gets us unique identifiers for each of the news shows. An identifier is a simple string that combines channel_name, show_name, time, and date. The current final list of identifiers (2009--Nov. 2017) is posted [here](data/search.csv). 

2. Next, we use the identifier to build a URL where the metadata file and HTML file with the closed captions is posted. The general base URL is http://archive.org/download followed by the identifier.

3. The third script parses the downloaded metadata and HTML closed caption files and creates a CSV along with the meta data.

For instance, we will go http://archive.org/download/CSPAN_20090604_230000 for identifier `CSPAN_20090604_230000` And from http://archive.org/download/CSPAN_20090604_230000/CSPAN_20090604_230000_meta.xml, we read the link http://archive.org/details/CSPAN_20090604_230000, from which we get the text from HTML file. We also store the meta data from the META XML file.

### Scripts

1. **Get Show Identifiers**  
    - [Get Identifiers For Each Show (Channel, Show, Date, Time)](scripts/get_news_identifiers.py)
    - Produces [data/search.csv](data/search.csv)

2. **Download Metadata and HTML Files**  
    - [Download the Metadata and HTML Files](scripts/scrape_archive_org.py)
    - Saves the metadata and HTML files to two separate folders specified in `--meta` and `--html` respectively. The default folder names are `meta` and `html` respectively.

3. **Parse Metadata and HTML Files**  
    - [Parses metadata and HTML Files and Saves to a CSV](scripts/parse_archive.py)
    - Produces a CSV. [Here's an example](data/archive-out.csv)

### Running the Scripts

1. Get all TV Archive identifiers from archive.org.  

    ```
    python get_news_identifiers.py -o ../data/search.csv
    ```

2. Download metadata and HTML files for all the shows in the [sample input file](data/search-test.csv)  

    ```
    python scrape_archive_org.py ../data/search-test.csv
    ```

    This will create two directories `meta` and `html` by default in the same folder as where the script is. We have included the first [25 metadata](data/meta/) and first 25 [html files](data/html/).  

    You can change the folder for `meta` by using the `--meta` flag. To change the directory for `html`, use the `--html` flag and specify the new directory. For instance,  

    ```
    python scrape_archive_org.py --meta meta-foxnews --html html-foxnews ../data/search-test.csv
    ```

    Use `-c/--compress` option to store and parse the downloaded files in compression format (GZip).

3. Parse and extract meta fields and text from [sample metadata](data/meta) and [HTML files](data/html). 

    ```
    python parse_archive.py ../data/search-test.csv
    ```

    A [sample output file](data/archive-out.csv).

### License

We are releasing the scripts under the [MIT License](https://opensource.org/licenses/MIT).
