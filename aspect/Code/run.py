from extract import *
from aspects import *

def main():
    # CHANGE THE PATHS HERE
    # absolute path of yelp_academic_dataset_business.json
    business_file = '../../../yelp_academic_dataset_business.json'
    # absolute path of yelp_academic_dataset_review.json
    review_file = '../../../yelp_academic_dataset_review.json'

    # path of file storing all the restaurant businesses
    restaurant_file = '../Data/restaurants.json'
    # path of file storing all the restaurant reviews
    restaurant_review_file = '../Data/restaurant_reviews.json'
    # path of file storing ids of all the restaurants whose reviews we have filtered
    filtered_restaurant_file = '../Data/filtered_restaurants.txt'

    # path of the positive review file
    positive_review_file = '../Data/positive_reviews.json'
    # path of the negative review train file
    negative_train_review_file = '../Data/negative_train_reviews.json'
    # path of the negative review test file
    negative_test_review_file = '../Data/negative_test_reviews.json'
    # the complete training set with all the negative train and positive reviews
    filtered_dataset = '../Data/filtered_dataset.json'

    extract_restaurants(business_file, restaurant_file)
    extract_reviews_for_restaurants(
        restaurant_file, review_file, restaurant_review_file, filtered_restaurant_file)
    extract_positive_and_negative_reviews(
        restaurant_review_file, filtered_restaurant_file, filtered_dataset, positive_review_file, negative_train_review_file, negative_test_review_file)
    get_statistics(filtered_dataset)

    train_file = '../Data/filtered_dataset.json'
    dependency_file = '../Data/dependencies.txt'
    aspect_file = '../Data/aspects.txt'

    retcode = server.start_corenlp_server()
    if retcode != 0:
        exit(retcode)
    
    get_dependencies(train_file, dependency_file)

    retcode = server.stop_corenlp_server()
    if retcode != 0:
        print('Failed to shutdown server properly!Please check and shut it down.')

    get_aspects(dependency_file, aspect_file)

if __name__ == '__main__':
    main()