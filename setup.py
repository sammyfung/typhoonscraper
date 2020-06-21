from setuptools import setup, find_packages
setup(
    name="typhoonscraper",
    version="0.1",
    packages=find_packages(),
    entry_points={'scrapy': ['settings = typhoonscraper.settings']},
)
