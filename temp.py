import requests
import time
import os

url = "https://api.github.com/graphql"

# Use an environment variable for the token
token = "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"

headers = {
    "Authorization": f"Bearer {token}"
}

query = """
query ($queryString: String!, $after: String) {
  search(query: $queryString, type: USER, first: 100, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on User {
        login
        name
        repositories(first: 100, orderBy: {field: STARGAZERS, direction: DESC}) {
          totalCount
          nodes {
            stargazerCount
          }
        }
      }
    }
  }
}
"""

variables = {
    "queryString": "location:Dublin Ireland sort:repositories-desc"
}

users = []
has_next_page = True
after = None

while has_next_page:
    variables["after"] = after
    try:
        response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
        response.raise_for_status()  # This will raise an exception for HTTP errors

        data = response.json()
        if "errors" in data:
            print(f"GraphQL Errors: {data['errors']}")
            break

        search_data = data["data"]["search"]
        users.extend(search_data["nodes"])
        has_next_page = search_data["pageInfo"]["hasNextPage"]
        after = search_data["pageInfo"]["endCursor"]

        # Respect rate limits
        time.sleep(2)
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if response.status_code == 403:
            print("You might have hit a rate limit. Wait for a while before trying again.")
        break


def get_total_stars(user):
    return sum(repo['stargazerCount'] for repo in user['repositories']['nodes'])


# Sort users by star count
users.sort(key=get_total_stars, reverse=True)

# Print top 10 users
print("\nTop 10 users with most stars on their repositories in Dublin, Ireland:")
for i, user in enumerate(users[:10], 1):
    total_stars = get_total_stars(user)
    print(f"{i}. {user['login']} ({user['name'] or 'No name'}): {total_stars} stars")