# (C) Copyright 2020 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

try:
    import ipywidgets  # noqa
    from tqdm.auto import tqdm
except ImportError:
    from tqdm import tqdm


from climetlab.core.thread import SoftThreadPool

from .multi import MultiSource
from .url import Url


class MultiUrl(MultiSource):
    def __init__(self, urls, *args, filter=None, merger=None, force=None, **kwargs):
        if not isinstance(urls, (list, tuple)):
            urls = [urls]

        nthreads = min(self.settings("number-of-download-threads"), len(urls))

        if nthreads < 2:
            sources = [Url(url, force=force) for url in urls]
        else:
            with SoftThreadPool(nthreads=nthreads) as pool:

                futures = [
                    pool.submit(Url, url, watcher=pool, force=force) for url in urls
                ]

                iterator = (f.result() for f in futures)
                sources = list(tqdm(iterator, leave=True, total=len(urls)))

        super().__init__(sources, filter=filter, merger=merger)
