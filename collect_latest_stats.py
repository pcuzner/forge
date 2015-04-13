#!/usr/bin/env python
"""Collect the latest social stats for Gluster projects

Grabs watchers, stars, forks.
Needs code added to grab # of commits per day, and total downloads per day
(when available).

Requires the SQLite3 Python module
"""

import os, os.path, ConfigParser
import sqlite3
import requests
import json

# Enable this to have the results printed to stdout
debug = True

# Read the GitHub projects from the ./config file
config_file_path = 'config'
config = ConfigParser.SafeConfigParser()
config.read(config_file_path)

# Open the ./stats.db SQLite3 database
db_path = 'db/project_stats.db'
conn = sqlite3.connect(db_path)

# Connect to the database
c = conn.cursor()

# Create the SQLite3 table to store the info, if it's not already present
sql = ('CREATE TABLE IF NOT EXISTS social_stats '
       '(project TEXT, time_stamp TEXT, watchers INTEGER, stars INTEGER, '
       'forks INTEGER)')
c.execute(sql)
conn.commit()

# Loop through the projects in the config file
for project in config.sections():

    # Construct the GitHub API URL for the project
    api_url = 'https://api.github.com/repos/' + project

    # Retrieve the (json) API page
    api_page = requests.get(api_url, verify=True)
    if api_page.status_code != 200:
        print 'Error retrieving API page {0}'.format(api_url)
        print '  Status code {0} : {1}'.format(api_page.status_code)
    json_data = json.loads(api_page.text)

    # Extract the number of watchers
    watchers = json_data['watchers']

    # Extract the number of stars
    stars = json_data['stargazers_count']

    # Extract the number of forks
    forks = json_data['forks_count']

    # Print the results to stdout
    if debug:
        print 'watchers: {0}\tstars: {1}\tforks: {2}'.format(watchers,
                                                             stars, forks)

    # Add the results to the database
    sql = ('INSERT INTO social_stats '
           '(project, time_stamp, watchers, stars, forks) '
           'VALUES '
           "('{0}', date('now'), '{1}', '{2}', '{3}')").format(project,
                                                               watchers,
                                                               stars, forks)
    c.execute(sql)
    conn.commit()

# Close the database connection
c.close()