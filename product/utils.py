import pandas as pd
from django.core.cache import cache
from django.db.models import Count, Avg
from sklearn.model_selection import train_test_split
from sklearn.decomposition import TruncatedSVD
from product.models import Item
from users.models import UserActivity
from product.models import Rating


# Load user activity data and return DataFrame
def load_user_activity_data(user_id, min_interactions):
    activity = UserActivity.objects.filter(user_id=user_id).select_related("item")
    activity = activity.values(
        "user_id",
        "item__id",
        "item__product_category__name",
        "item__product_type__name",
        "activity_type",
        "timestamp",
    )
    activity = activity.annotate(count=Count("activity_type"))
    df = pd.DataFrame.from_records(activity)

    return df


# Load user ratings data and return DataFrame
def load_user_ratings_data(user_id):
    ratings = Rating.objects.filter(user__id=user_id).select_related("item")
    ratings = ratings.values("user", "item__id", "stars")
    ratings_df = pd.DataFrame.from_records(ratings)
    ratings_df = ratings_df.pivot_table(index=["user", "item__id"], values="stars")
    return ratings_df


# Calculate item popularity based on average ratings
def calculate_item_popularity():
    item_ratings = Rating.objects.values("item__id").annotate(avg_rating=Avg("stars"))
    item_popularity = {item["item__id"]: item["avg_rating"] for item in item_ratings}
    return item_popularity


# Perform collaborative filtering and return recommended items
def perform_collaborative_filtering(df, ratings_df, n_components, test_size):
    # Convert the data to a user-item interaction matrix
    user_item_matrix = df.pivot_table(
        index="user_id", columns="item__id", values="count", fill_value=0
    )

    # Split the data into training and test sets
    X_train, X_test = train_test_split(
        user_item_matrix, test_size=test_size, random_state=42
    )

    # Use TruncatedSVD to fit a collaborative filtering model on the training data
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    svd.fit(X_train)

    # Use the model to transform the training data to its lower-dimensional representation
    X_train_svd = svd.transform(X_train)

    # Get the indices of the items in the test set (which are the columns of the user_item_matrix)
    item_indices = X_train.columns.get_indexer(X_test.columns)

    # Get the indices of the users in the test set (which are the rows of the user_item_matrix)
    user_indices = X_train.index.get_indexer(X_test.index)

    # Get the predictions for the test set
    predicted_ratings = X_train_svd[user_indices, :].dot(
        svd.components_[:, item_indices]
    )

    # Convert the predicted ratings to a DataFrame with user and item indices
    predicted_ratings_df = pd.DataFrame(
        predicted_ratings, index=X_test.index, columns=X_test.columns
    )

    # Get the top N recommended items for each user
    recommended_items = predicted_ratings_df.apply(
        lambda row: row.nlargest(10).index.tolist(), axis=1
    )

    return recommended_items


# Get the top N recommended items based on popularity score and return as queryset
def get_top_recommended_items(recommended_items, item_popularity, n):
    # Calculate a popularity score for each recommended item based on average ratings
    recommended_items["popularity_score"] = recommended_items["item__id"].map(
        item_popularity
    )

    # Sort the recommended items based on popularity score in descending order
    recommended_items = recommended_items.sort_values(
        by="popularity_score", ascending=False
    )

    # Get the top N recommended items
    recommended_items = recommended_items.head(n)

    # Retrieve the recommended items from the Item model based on their IDs
    item_ids = recommended_items["item__id"].tolist()
    recommended_items = Item.objects.filter(id__in=item_ids)

    return recommended_items


# Use caching for frequently requested recommendations
def get_precomputed_recommendations(user_id):
    cache_key = f"precomputed_recs_{user_id}"
    recommended_items = cache.get(cache_key)
    return recommended_items


# Update the precomputed recommendations asynchronously
def update_precomputed_recommendations(df, ratings_df, n_components, test_size):
    precomputed_recs = perform_collaborative_filtering(
        df, ratings_df, n_components, test_size
    )
    user_id = "global"  # Use a global key for all users' precomputed recommendations
    cache_key = f"precomputed_recs_{user_id}"
    cache.set(
        cache_key, precomputed_recs, timeout=None
    )  # Set timeout=None for indefinite caching


# Create recommendation function using collaborative filtering with user ratings and item popularity
def recommend_items(
    user_id, n=10, min_interactions=5, n_components=10, test_size=0.2, time_decay=True
):
    # Load user activity data and user ratings data
    df = load_user_activity_data(user_id, min_interactions)
    ratings_df = load_user_ratings_data(user_id)

    print(df, ratings_df)

    # Check if there is enough data to make recommendations
    if len(df) <= 1:
        # If not, return the available items
        item_ids = df.index.get_level_values("item__id")
        recommended_items = Item.objects.filter(id__in=item_ids)[:n]
        return recommended_items

    # Calculate item popularity based on average ratings
    item_popularity = calculate_item_popularity()

    # Fetch precomputed recommendations for the user (if available and time_decay is True)
    if time_decay:
        recommended_items = get_precomputed_recommendations(user_id)

    # If precomputed recommendations are not available or time_decay is False, perform real-time recommendations
    if not recommended_items:
        # Perform collaborative filtering and get recommended items
        recommended_items = perform_collaborative_filtering(
            df, ratings_df, n_components, test_size
        )

    # Get the top N recommended items based on popularity score
    recommended_items = get_top_recommended_items(recommended_items, item_popularity, n)

    # Update the precomputed recommendations asynchronously (if time_decay is True)
    if time_decay:
        import asyncio

        asyncio.create_task(
            update_precomputed_recommendations(df, ratings_df, n_components, test_size)
        )

    return recommended_items


# Main function to recommend items for a user
# if __name__ == "__main__":
#     user_id = 123  # Replace with the user ID for whom recommendations are needed
#     recommended_items = recommend_items(user_id)
#     for item in recommended_items:
#         print(item.product_name)
