import json
from collections import defaultdict, Counter
import server
from nltk.parse import CoreNLPParser
import sys
from matplotlib import pyplot as plt
import random

CLEAR_LINE = '\033[K'

# TWEAKABLE PARAMS - CHANGE THESE AS PER NEED
MIN_REVIEWS_FOR_RESTAURANT = 800
MIN_WORDS_IN_REVIEW = 20
MAX_WORDS_IN_REVIEW = 300
MAX_TEST_REVIEWS = 250
MAX_REVIEWS_PER_RESTAURANT = 120
THRESHOLD_STAR_RATING = 3

# get all the businesses that are restaurants
def extract_restaurants(business_file, restaurant_file):
    stop_file = '../Data/stop_list.txt'

    stop_list = []
    with open(stop_file, 'r') as fin:
        for line in fin:
            stop_list.append(line.strip().lower())
    
    restaurants = []
    count = 0
    with open(business_file, 'r') as fin:
        for line in fin:
            business = json.loads(line)
            categories = business['categories']
            if categories is None:
                continue            
            # Filter restaurants based on location
            if not business['city'].lower() == "las vegas":
                continue
            # if restaurant is one of the business categories
            if 'restaurant'.casefold() in categories.casefold():
                categories = categories.strip().lower() 
                ok = True
                for stop_cat in stop_list:
                    if stop_cat in categories:
                        ok = False
                        break
                if ok:
                    count += 1
                    restaurants.append(business)

    print(count, 'restaurants are present.')
    with open(restaurant_file, 'w') as fout:
        for restaurant in restaurants:
            fout.write(json.dumps(restaurant) + '\n')

# extract all the reviews for the restaurant businesses
def extract_reviews_for_restaurants(restaurant_file, review_file, restaurant_review_file, filtered_restaurant_file):
    restaurant_ids = set()
    with open(restaurant_file, 'r') as fin:
        for line in fin:
            restaurant = json.loads(line)
            restaurant_ids.add(restaurant['business_id'])
    print(len(restaurant_ids), 'restaurant ids.')

    reviews = []
    num_reviews = 0

    max_batch_sz = 10000
    batch_sz = 0
    batch_num = 1

    # store the length frequency of the reviews
    length_map = defaultdict(int)
    # store the restaurant frequency
    restaurant_map = Counter()

    with open(review_file, 'r') as fin, open(restaurant_review_file, 'w') as fout:
        for line in fin:
            review = json.loads(line)
            if review['business_id'] in restaurant_ids:
                review_text = review['text'].lower()
                length_map[len(review_text)] += 1
                restaurant_map[review['business_id']] += 1

                num_reviews += 1
                batch_sz += 1

                reviews.append(review)

            if batch_sz == max_batch_sz:
                print('Writing batch', batch_num, 'to file.', end='\r')
                for review in reviews:
                    fout.write(json.dumps(review) + '\n')
                reviews.clear()
                batch_sz = 0
                batch_num += 1
        if batch_sz > 0:
            print('Writing batch', batch_num, 'to file.', end='\r')
            for review in reviews:
                fout.write(json.dumps(review) + '\n')
            reviews.clear()

    print('{}{} batches'.format(CLEAR_LINE, batch_num))
    print(num_reviews, 'restaurant reviews')

    with open('../Logs/freq.log', 'w') as logfile, open(filtered_restaurant_file, 'w') as fout:
        # logfile.write('length freq map\n')
        # for length, freq in length_map.items():
        #     logfile.write(
        #         '{} length reviews occur {} times.\n'.format(length, freq))
        # logfile.write('==================================================================')
        logfile.write('restaurant freq map\n')
        for restaurant, freq in restaurant_map.most_common():
            logfile.write('{} restaurant: {} reviews.\n'.format(restaurant, freq))
            if freq >= MIN_REVIEWS_FOR_RESTAURANT:
                fout.write(restaurant + '\n')

    # plot restaurant vs freq of reviews for each
    # restaurant
    plt.clf()    
    plt.bar(range(1, len(restaurant_map.keys()) + 1), restaurant_map.values())    
    plt.xlabel('restaurant')
    plt.ylabel('freq')

    plt.tight_layout()
    plt.savefig('../Logs/freq.jpeg')

    # plt.show()


# separate reviews into positive and negative based on star rating
# also filter out reviews that are too small or too large
def extract_positive_and_negative_reviews(restaurant_review_file, filtered_restaurant_file, filtered_dataset, positive_file, negative_train_file, negative_test_file):
    pos = 0
    neg_train = 0
    neg_test = 0
    THRESHOLD_STAR_RATING = 3

    pos_reviews = []
    neg_train_reviews = []
    neg_test_reviews = []

    max_batch_sz = 10000
    batch_sz = 0
    batch_num = 1

    restaurant_ids = set()
    with open(filtered_restaurant_file, 'r') as fin:
        for line in fin:
            restaurant_ids.add(line.strip())

    restaurant_map = defaultdict(int)
    with open(restaurant_review_file, 'r') as fin, open(positive_file, 'w') as fposout, open(negative_train_file, 'w') as fnegtrainout, open(negative_test_file, 'w') as fnegtestout, open(filtered_dataset, 'w') as fout:
        test = False
        for line in fin:
            review = json.loads(line)
            restaurant_id = review['business_id']
            if restaurant_id not in restaurant_ids or restaurant_map[restaurant_id] >= MAX_REVIEWS_PER_RESTAURANT:
                continue
            review_text = review['text']
            num_words = len(review_text.split())
            if num_words < MIN_WORDS_IN_REVIEW or num_words > MAX_WORDS_IN_REVIEW:
                continue
            
            restaurant_map[restaurant_id] += 1
            if review['stars'] > THRESHOLD_STAR_RATING:
                pos += 1
                pos_reviews.append(review)
            else:
                if test and neg_test < MAX_TEST_REVIEWS:
                    neg_test += 1
                    neg_test_reviews.append(review)
                    test = False
                else:
                    neg_train += 1
                    neg_train_reviews.append(review)
                    test = True
            batch_sz += 1
            if batch_sz == max_batch_sz:
                print('Writing batch {} to file, {} positive reviews, {} negative train reviews, {} negative test reviews.'.format(
                    batch_num, len(pos_reviews), len(neg_train_reviews), len(neg_test_reviews)), end='\r')
                for pos_review in pos_reviews:
                    fposout.write(json.dumps(pos_review) + '\n')
                    fout.write(json.dumps(pos_review) + '\n')
                for neg_train_review in neg_train_reviews:
                    fnegtrainout.write(json.dumps(neg_train_review) + '\n')
                    fout.write(json.dumps(neg_train_review) + '\n')
                for neg_test_review in neg_test_reviews:
                    fnegtestout.write(json.dumps(neg_test_review) + '\n')
                    # fout.write(json.dumps(neg_test_review) + '\n')
                batch_sz = 0
                pos_reviews.clear()
                neg_train_reviews.clear()
                neg_test_reviews.clear()
                batch_num += 1

        if batch_sz > 0:
            print('Writing batch {} to file, {} positive reviews, {} negative train reviews, {} negative test reviews.'.format(
                batch_num, len(pos_reviews), len(neg_train_reviews), len(neg_test_reviews)), end='\r')
            for pos_review in pos_reviews:
                fposout.write(json.dumps(pos_review) + '\n')
                fout.write(json.dumps(pos_review) + '\n')
            for neg_train_review in neg_train_reviews:
                fnegtrainout.write(json.dumps(neg_train_review) + '\n')
                fout.write(json.dumps(neg_train_review) + '\n')
            for neg_test_review in neg_test_reviews:
                fnegtestout.write(json.dumps(neg_test_review) + '\n')
            pos_reviews.clear()
            neg_train_reviews.clear()
            neg_test_reviews.clear()

    print('{}{} batches'.format(CLEAR_LINE, batch_num))
    print(pos, 'positive restaurant reviews')
    print(neg_train, 'negative train restaurant reviews')
    print(neg_test, 'negative test restaurant reviews')
    print('total number of filtered reviews(train) = {}'.format(str(pos + neg_train)))

    
# get statistics like length frequency, restaurant frequency and user frequency
def get_statistics(dataset):
    length_map = defaultdict(int)
    restaurant_map = defaultdict(int)
    user_map = defaultdict(int)

    with open(dataset, 'r') as fin:
        pos = 0
        neg = 0
        for line in fin:
            review = json.loads(line)
            review_text = review['text']
            user_id = review['user_id']
            restaurant_id = review['business_id']
            stars = review['stars']
            if stars > THRESHOLD_STAR_RATING:
                pos += 1
            else:
                neg += 1
            review_len = len(review_text)
            length_map[review_len] += 1
            restaurant_map[restaurant_id] += 1
            user_map[user_id] += 1

    parts = dataset.split('/')
    parts[-1] = 'statistics_' + parts[-1]
    parts[-1] = parts[-1].replace('json', 'txt')
    dataset = '/'.join(part for part in parts)
    with open(dataset, 'w') as fout:
        fout.write('{} different lengths.\n'.format(len(length_map.keys())))
        fout.write('{} different restaurants.\n'.format(len(restaurant_map.keys())))
        fout.write('{} different users.\n'.format(len(user_map.keys())))
        fout.write('\n{} positive train reviews.\n'.format(pos))
        fout.write('{} negative train reviews.\n'.format(neg))
        fout.write('{} negative test reviews.\n'.format(MAX_TEST_REVIEWS))
        # fout.write('Length Freq Map\n')
        # for length, freq in length_map.items():
        #     fout.write('{}\t:{}\n'.format(length, freq))
        fout.write('\nRestaurant Freq Map\n')
        for restaurant, freq in restaurant_map.items():
            fout.write('{}\t:{}\n'.format(restaurant, freq))
        # fout.write('User Freq Map\n')
        # for user, freq in user_map.items():
        #     fout.write('{}\t:{}\n'.format(user, freq))


if __name__ == '__main__':
    # change the paths here as per your system
    business_file = '/home/rohan/Documents/yelp_dataset/yelp_academic_dataset_business.json'
    restaurant_file = '../Data/restaurants.json'
    review_file = '/home/rohan/Documents/yelp_dataset/yelp_academic_dataset_review.json'
    restaurant_review_file = '../Data/restaurant_reviews.json'
    positive_review_file = '../Data/positive_reviews.json'
    negative_train_review_file = '../Data/negative_train_reviews.json'
    negative_test_review_file = '../Data/negative_test_reviews.json'
    filtered_restaurant_file = '../Data/filtered_restaurants.txt'
    filtered_dataset = '../Data/filtered_dataset.json'

    extract_restaurants(business_file, restaurant_file)
    extract_reviews_for_restaurants(
        restaurant_file, review_file, restaurant_review_file, filtered_restaurant_file)
    extract_positive_and_negative_reviews(
        restaurant_review_file, filtered_restaurant_file, filtered_dataset, positive_review_file, negative_train_review_file, negative_test_review_file)
    get_statistics(filtered_dataset)

    
