import os
import json
import pkgutil

import pandas as pd

from vega_datasets._compat import urlopen, BytesIO, bytes_decode


def _load_dataset_info():
    """This loads dataset info from two package files:

    vega_datasets/datasets.json
    vega_datasets/data/listing.txt

    It returns a dictionary with dataset information.
    """
    info = pkgutil.get_data('vega_datasets', 'datasets.json')
    info = json.loads(bytes_decode(info))

    local = pkgutil.get_data('vega_datasets', 'data/listing.txt')
    local = bytes_decode(local).split()

    for name in info:
        info[name]['is_local'] = (name in local)

    return info


class Dataset(object):
    """Class to load a particular dataset by name"""

    _instance_doc = """Loader for the {name} dataset.
    {data_description}
    {bundle_info}
    Dataset source: {url}

    Usage
    -----

        >>> from vega_datasets import data
        >>> df = data.{methodname}()
        >>> type(df)
        pandas.core.frame.DataFrame

    Equivalently, you can use

        >>> df = data('{name}')

    To get the raw dataset rather than the dataframe, use

        >>> data_bytes = data.{methodname}.raw()
        >>> type(data_bytes)
        bytes

    To find the dataset url, use

        >>> data.{methodname}.url
        '{url}'
    {additional_docs}
    Attributes
    ----------
    filename : string
        The filename in which the dataset is stored
    url : string
        The full URL of the dataset at http://vega.github.io
    format : string
        The format of the dataset: usually one of {{'csv', 'tsv', 'json'}}
    pkg_filename : string
        The path to the local dataset within the vega_datasets package
    is_local : bool
        True if the dataset is available locally in the package
    filepath : string
        If is_local is True, the local file path to the dataset.

    Reference
    ---------
    {reference_info}
    """
    _data_description = ""
    _additional_docs = ""
    _reference_info = """
    For information on this dataset, see https://github.com/vega/vega-datasets/
    """
    base_url = 'https://vega.github.io/vega-datasets/data/'
    _dataset_info = _load_dataset_info()
    _pd_read_kwds = {}

    @classmethod
    def init(cls, name):
        """Return an instance of this class or an appropriate subclass"""
        clsdict = {subcls.name: subcls for subcls in cls.__subclasses__()
                   if hasattr(subcls, 'name')}
        return clsdict.get(name, cls)(name)

    def __init__(self, name):
        info = self._infodict(name)
        self.name = name
        self.methodname = name.replace('-', '_')
        self.filename = info['filename']
        self.url = self.base_url + info['filename']
        self.format = info['format']
        self.pkg_filename = 'data/' + self.filename
        self.is_local = info['is_local']
        if self.is_local:
            bundle_info = ("This dataset is bundled with vega_datasets; "
                           "it can be loaded without web access.")
        else:
            bundle_info = ("This dataset is not bundled with vega_datasets; "
                           "it requires web access to load.")
        self.__doc__ = self._instance_doc.format(additional_docs=self._additional_docs,
                                                 reference_info=self._reference_info.lstrip(),
                                                 data_description=self._data_description,
                                                 bundle_info=bundle_info,
                                                 **self.__dict__)

    @classmethod
    def list_datasets(cls):
        """Return a list of names of available datasets"""
        return sorted(cls._dataset_info.keys())

    @classmethod
    def list_local_datasets(cls):
        return sorted(name for name, info in cls._dataset_info.items()
                      if info['is_local'])

    @classmethod
    def _infodict(cls, name):
        """load the info dictionary for the given name"""
        info = cls._dataset_info.get(name, None)
        if info is None:
            raise ValueError('No such dataset {0} exists, '
                             'use list_datasets() to get a list '
                             'of available datasets.'.format(name))
        return info

    def raw(self, use_local=True):
        """Load the raw dataset from remote URL or local file

        Parameters
        ----------
        use_local : boolean
            If True (default), then attempt to load the dataset locally. If
            False or if the dataset is not available locally, then load the
            data from an external URL.
        """
        if use_local and self.is_local:
            return pkgutil.get_data('vega_datasets', self.pkg_filename)
        else:
            return urlopen(self.url).read()

    def dataframe(self, use_local=True, **kwargs):
        """Load the dataset from remote URL or local file

        Parameters
        ----------
        use_local : boolean
            If True (default), then attempt to load the dataset locally. If
            False or if the dataset is not available locally, then load the
            data from an external URL.
        **kwargs :
            additional keyword arguments are passed to pd.read_json() or
            pd.read_csv(), depending on the format of the data source
        """
        datasource = BytesIO(self.raw(use_local))

        kwds = self._pd_read_kwds.copy()
        kwds.update(kwargs)

        if self.format == 'json':
            return pd.read_json(datasource, **kwds)
        elif self.format == 'csv':
            return pd.read_csv(datasource, **kwds)
        elif self.format == 'tsv':
            kwargs['sep'] = '\t'
            return pd.read_csv(datasource, **kwds)
        else:
            raise ValueError("Unrecognized file format: {0}. "
                             "Valid options are ['json', 'csv', 'tsv']."
                             "".format(self.format))

    __call__ = dataframe

    @property
    def filepath(self):
        if not self.is_local:
            raise ValueError("filepath is only valid for local datasets")
        else:
            return os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                'data', self.filename))


class Stocks(Dataset):
    name = 'stocks'
    _data_description = """
    Daily closing stock prices for AAPL, AMZN, GOOG, IBM, and MSFT
    between 2000 and 2010.
    """
    _additional_docs = """
    For convenience, the stocks dataset supports pivoted output using the
    optional `pivoted` keyword. If pivoted is set to True, each company's
    price history will be returned in a separate column:

        >>> df = data.stocks()  # not pivoted
        >>> df.head(3)
          symbol       date  price
        0   MSFT 2000-01-01  39.81
        1   MSFT 2000-02-01  36.35
        2   MSFT 2000-03-01  43.22

        >>> df_pivoted = data.stocks(pivoted=True)
        >>> df_pivoted.head()
        symbol       AAPL   AMZN  GOOG     IBM   MSFT
        date
        2000-01-01  25.94  64.56   NaN  100.52  39.81
        2000-02-01  28.66  68.87   NaN   92.11  36.35
        2000-03-01  33.95  67.00   NaN  106.11  43.22
    """
    _pd_read_kwds = {'parse_dates': ['date']}

    def dataframe(self, pivoted=False, use_local=True, **kwargs):
        data = super(Stocks, self).dataframe(use_local=use_local, **kwargs)
        if pivoted:
            data = data.pivot(index='date', columns='symbol', values='price')
        return data

    __call__ = dataframe


class Anscombe(Dataset):
    name = 'anscombe'
    _data_description = """
    Anscombe's Quartet is a famous dataset constructed by Francis Anscombe [1]_.
    Common summary statistics are identical for each subset of the data, despite
    the subsets having vastly different characteristics.
    """
    _reference_info = """
    This dataset was originally proposed by Francis Anscombe:

    .. [1] Anscombe, F. J. (1973). "Graphs in Statistical Analysis".
       American Statistician. 27 (1): 17–21. JSTOR 2682899.
    """

class Barley(Dataset):
    name = 'barley'
    _data_description = """
    This dataset contains crop yields over different regions and different
    years in the 1930s. It was originally published by Immer in 1934 [1]_.
    """
    _reference_info = """
    This dataset was originally published by Immer (1934), and was popularized
    by Fisher (1947) and Cleveland (1993).

    .. [1] Immer, F.R., Hayes, H.D. and LeRoy Powers (1934)
       Statistical determination of barley varietal adaptation.
       Journal of the American Society for Agronomy 26, 403–419.

    .. [2] Fisher, R.A. (1947) The Design of Experiments. 4th edition.
       Edinburgh: Oliver and Boyd.

    .. [3] Cleveland, WS (1993) Visualizing data. Hobart Press
    """


class Cars(Dataset):
    name = 'cars'
    _reference_info = """
    This dataset appeared originally at http://lib.stat.cmu.edu/datasets/

    .. [1] Donoho, David and Ramos, Ernesto (1982), ``PRIMDATA:
           Data Sets for Use With PRIM-H'' (DRAFT).
    """
    _pd_read_kwds = {'convert_dates': ['Year']}


class Crimea(Dataset):
    name = 'crimea'
    _dataset_info = """
    This dataset was originally published in 1958 by Florence Nightingale [1]_
    in connection with her famous "Coxcomb" charts
    """
    _reference_info = """
    .. [1] Nightingale, Florence (1858) "Notes on Matters Affecting the Health,
       Efficiency and Hospital Administration of the British Army" RCIN 1075240
    """


class SeattleTemps(Dataset):
    name = 'seattle-temps'
    _reference_info = """
    This dataset is drawn from public-domain
    `NOAA data <https://www.weather.gov/disclaimer>`_, and transformed
    using scripts available at http://github.com/vega/vega_datasets/
    """
    _pd_read_kwds = {'parse_dates': ['date']}


class SeattleWeather(Dataset):
    name = 'seattle-weather'
    _reference_info = """
    This dataset is drawn from public-domain
    `NOAA data <https://www.weather.gov/disclaimer>`_, and transformed
    using scripts available at http://github.com/vega/vega_datasets/
    """
    _pd_read_kwds = {'parse_dates': ['date']}


class SFTemps(Dataset):
    name = 'sf-temps'
    _reference_info = """
    This dataset is drawn from public-domain
    `NOAA data <https://www.weather.gov/disclaimer>`_, and transformed
    using scripts available at http://github.com/vega/vega_datasets/
    """
    _pd_read_kwds = {'parse_dates': ['date']}


class DataLoader(object):
    """Load a dataset from a local file or remote URL.

    There are two ways to call this; for example to load the iris dataset, you
    can call this object and pass the dataset name by string:

        >>> from vega_datasets import data
        >>> df = data('iris')

    or you can call the associated named method:

        >>> df = data.iris()

    Optionally, additional parameters can be passed to either of these

    Optional parameters
    -------------------
    return_raw : boolean
        If True, then return the raw string or bytes.
        If False (default), then return a pandas dataframe.
    use_local : boolean
        If True (default), then attempt to load the dataset locally. If
        False or if the dataset is not available locally, then load the
        data from an external URL.
    **kwargs :
        additional keyword arguments are passed to the pandas parsing function,
        either ``read_csv()`` or ``read_json()`` depending on the data format.
    """
    _datasets = {name.replace('-', '_'): name
                 for name in Dataset.list_datasets()}

    def list_datasets(self):
        return Dataset.list_datasets()

    def list_local_datasets(self):
        return Dataset.list_local_datasets()

    def __call__(self, name, return_raw=False, use_local=True, **kwargs):
        loader = getattr(self, name.replace('-', '_'))
        if return_raw:
            return loader.raw(use_local=use_local, **kwargs)
        else:
            return loader(use_local=use_local, **kwargs)

    def __getattr__(self, dataset_name):
        if dataset_name in self._datasets:
            return Dataset.init(self._datasets[dataset_name])
        else:
            raise AttributeError("No dataset named '{0}'".format(dataset_name))

    def __dir__(self):
        return list(self._datasets.keys())
