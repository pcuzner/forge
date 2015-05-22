#!/usr/bin/env python

"""Collect the latest social stats for Gluster projects

Grabs watchers, stars, forks, # of commits per day, and total number of downloads (ever).

Known Issues
1. uses anonymous github interaction which is ratelimited to 60 calls from the same IP per hour - so this won't scale
   with the gluster github repos

Requires the SQLite3 Python module
"""

import os.path
import ConfigParser
import sqlite3
import json
import datetime
import requests


# Enable this to have the results printed to stdout
debug = True


class GitHubRequest(object):
    github_api_url = 'https://api.github.com/repos'

    def __init__(self):
        self.url = ''
        self.response_ok = True
        self.api_data = []

    def get_stats(self, request_type, description):
        self.url = '/'.join((GitHubRequest.github_api_url, request_type))
        api_page = requests.get(self.url, verify=True)
        if api_page.status_code == 200:
            self.api_data = json.loads(api_page.text)
        else:
            self.response_ok = False
            print 'Error retrieving data for {0}'.format(description)
            print '  Status code {0}'.format(api_page.status_code)


def main():

    # Read the GitHub projects from the ./config file
    base_path = os.path.dirname(os.path.realpath(__file__))
    config_file_path = os.path.join(base_path, 'config')
    config = ConfigParser.SafeConfigParser()
    config.read(config_file_path)

    db_path = os.path.join(base_path, 'db/project_stats.db')

    # Open the ./db/project_stats.db SQLite3 database
    conn = sqlite3.connect(db_path)

    # Connect to the database
    c = conn.cursor()

    # Create the SQLite3 table to store the info, if it's not already present
    sql = ('CREATE TABLE IF NOT EXISTS social_stats (project TEXT, time_stamp TEXT, '
           'watchers INTEGER, stars INTEGER, forks INTEGER, commits INTEGER, downloads INTEGER)')
    c.execute(sql)
    conn.commit()

    today = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    yesterday = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S')

    github = GitHubRequest()

    # Loop through the projects in the config file
    for project in config.sections():

        download_counter = 0

        # Query high level stats
        github.get_stats(request_type=project, description='API page')
        if github.response_ok:

            # Extract the number of watchers, stars, and forks
            watchers = github.api_data['subscribers_count']
            stars = github.api_data['stargazers_count']
            forks = github.api_data['forks_count']
        else:
            break

        # Count the # of commits in the last 24 hours
        github.get_stats(request_type='{0}/commits?since={1}Z'.format(project, yesterday),
                         description='commit data')
        if github.response_ok:

            commits_count = len(github.api_data)
        else:
            break

        # Retrieve the downloads page for this project
        github.get_stats(request_type='{0}/releases'.format(project),
                         description='downloads')
        if github.response_ok:

            # Note - For each project there is an outer loop of "releases" (eg v3.6.0), with an inner loop of "assets"
            # inside each release (with each asset having it's own download counter). eg: an .exe and a .dmg might be
            # two assets in the same v3.6.0 release.  The .exe might have 10,000 downloads, and the .dmg might
            # have 3,000.

            # Count how many downloads have occurred (ever) for the project
            if len(github.api_data) > 0:
                for release in github.api_data:
                    for asset in release['assets']:
                        download_counter += asset['download_count']
        else:
            break

        # Print the results to stdout for debugging
        if debug:
            print ('{0}\n\tcommits: {1}\twatchers: {2}\tstars: {3}\tforks: {4}\t'
                   'downloads: {5}\n'.format(project, commits_count, watchers, stars, forks, download_counter))

        # Add the results to the database
        sql = ('INSERT INTO social_stats (project, time_stamp, watchers, stars, forks, commits, downloads) VALUES '
               "('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')").format(project, today, watchers, stars, forks,
                                                                           commits_count, download_counter)
        c.execute(sql)
        conn.commit()

    # Close the database connection
    c.close()

if __name__ == '__main__':
    main()
