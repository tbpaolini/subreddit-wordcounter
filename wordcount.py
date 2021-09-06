import praw
from prawcore.exceptions import NotFound, RequestException, Redirect, ResponseException
from praw.exceptions import MissingRequiredAttributeException
from sys import exit
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

class WordCount:
    """The bot requests for a subreddit and a text input, then searches
    the 1000 most recent posts to find who has said it the most."""
    
    def __init__(self):
        try:
            print("Word Counter bot for Reddit: version 1.0.1 - by u/TiagoPaolini")
            self.reddit = praw.Reddit()
            print("Search the 1000 most recent posts of a subreddit in order to find who has said some word or sentence the most.")
        except MissingRequiredAttributeException:
            print("Error: praw.ini file not found. This file was supplied with the bot and should be on the same directory as the bot. Please do not change or remove it, unless you know what you are doing.")
            input("Press ENTER to exit program.")
            exit()
        except ResponseException:
            print("Error: praw.ini file has invalid credentials. This file was supplied with the bot and should be on the same directory as the bot. Please do not change or remove it, unless you know what you are doing.")
            input("Press ENTER to exit program.")
            exit()
    
    def main(self):
        while True:
            # Ask user to input a subreddit
            search_sub = input("Subreddit to search: r/")

            try:
                # Test if it is possible to connect to the subreddit
                self.subreddit = self.reddit.subreddit(search_sub)
                self.subreddit.id
                
            except RequestException:
                print("Error: You seem to be offline. Please connect to the internet and try again.")
                continue
            except NotFound:
                print("Error: Subreddit not found. Please check your spelling and try again.")
                continue
            except Redirect:
                print("Error: Subreddit not found. Please check your spelling and try again.")
                continue

            # Ask the user for a text to search:
            self.search_text = input("Text to search: ").lower().strip()

            # Do the search
            self.file_name = f"{self.subreddit.display_name}_word_count.txt"
            self.search_posts(self.search_text)
            print(f"Search finished. Full results were saved to {self.file_name}")

            # Do another search or close
            while True:
                user_input = input("Do you want to perform another search? [y]es / [n]: ").lower()
                if user_input.startswith("y"):
                    break
                elif user_input.startswith("n"):
                    print("Closing program... Have a nice day!")
                    exit()
    
    def search_posts(self, text):

        print(f"Fetching the list of recent posts on r/{self.subreddit.display_name} (up to 1000 posts)...")
        total_posts = 0
        total_posts_previous = -1
        total_comments = 0
        results_page = 0
        previous_post = ""
        posts_set = set()
        word_counter = Counter()
        
        # Get the most recent posts of the subreddit (up to 1000 posts)
        while (total_posts != total_posts_previous) and (results_page < 10):
            total_posts_previous = total_posts
            results_page += 1
            query_parameters = {"after": previous_post, "count": total_posts}

            # Loop through the result page
            for submission in self.subreddit.new(limit=100, params=query_parameters):
                total_posts += 1
                previous_post = submission.name
                total_comments += submission.num_comments
                posts_set.add(submission)
            
            # Keep updating the same line on terminal
            print(f"{total_posts} posts found ({total_comments} comments)", end="\r", flush=True)
        
        print(f"\nSearching for '{text}' in the content of posts... Please be patient.")
        
        # Search for the text on the post body and comments of all found submissions
        with ThreadPoolExecutor(max_workers=10) as executor:
            self._content_total = max(total_posts + total_comments, 1)
            self._content_count = 0
            results = executor.map(self.text_crawler, posts_set)
            for result in results:
                word_counter.update(result)
        print("Progress: 100%   ")

        # Output the results
        print("Search complete! Results:")
        
        user_column_width = 0
        count_column_width = 0

        for user, count in word_counter.items():    # Determine maximum column width of the results
            user_column_width = max(len(user) + 2, user_column_width)
            count_column_width = max(len(str(count)), count_column_width)

        # Save the results to file and show them on the terminal
        with open(self.file_name, "a", encoding="utf-8") as file:

            date = str(datetime.now())[:19] + "\n"
            titles = "User".ljust(user_column_width) + "\t" + "Count".rjust(count_column_width)
            header = f"'{self.search_text}' count on {date}\n{titles}\n"
            file.write(header)
            print("\n" + titles)

            line_count = 0
            for user, count in word_counter.most_common():
                line_count += 1
                user_str = ("u/" + user).ljust(user_column_width)
                count_str = str(count).rjust(count_column_width)
                line = f"{user_str}\t{count_str}"
                file.write(line + "\n")
                if line_count <= 10:
                    print(line)
            
            footer = "".ljust(user_column_width + count_column_width + 4, "-")
            file.write(f"\n{footer}\n\n")
            print(footer + "\n")


    def text_crawler(self, submission):
        post_word_counter = Counter()
        
        # Search the post body for the text
        if (submission.is_self) and (submission.author is not None):
            post_author = submission.author.name
            post_body = submission.selftext.lower()
            text_count = post_body.count(self.search_text)
            if text_count > 0:
                post_word_counter.update({post_author: text_count})
            self._content_count += 1
        
        # Search the post comments and count the ocurrences
        submission.comments.replace_more(limit=None)    # Get all comments of the post
        for comment in submission.comments.list():
            if comment.author is None:
                continue
            comment_author = comment.author.name
            comment_body = comment.body.lower()
            text_count = comment_body.count(self.search_text)
            if text_count > 0:
                post_word_counter.update({comment_author: text_count})
            self._content_count += 1
        
            # Print the progress
            print(f"Progress: {self._content_count * 100 / self._content_total:.2f}%", end="\r", flush=True)
        
        # Return the count on the current post
        return post_word_counter


if __name__ == "__main__":
    WordCount().main()