import pandas as pd
from django.core.cache import cache
from django.db.models import Avg
from sklearn.model_selection import train_test_split
from sklearn.decomposition import TruncatedSVD
from product.models import Item, Rating
from users.models import UserActivity

# Function to load data
load_data = lambda model, filters, values: pd.DataFrame.from_records(
    model.objects.filter(**filters).values(*values)
)


# Function to update cache
def update_cache(user, data):
    cache.set(f"precomputed_recs_{user}", data, timeout=None)


# Function to perform collaborative filtering on data
def perform_collaborative_filtering(ratings_df, n, n_components=10, test_size=0.2):
    # Creating a user-item matrix with ratings
    ui_matrix = ratings_df.pivot_table(
        index="user_id", columns="item__id", values="stars", fill_value=0
    )
    X_train, X_test = train_test_split(ui_matrix, test_size=test_size, random_state=42)

    # Applying SVD and making predictions
    svd = TruncatedSVD(n_components=n_components, random_state=42).fit(X_train)
    pred_ratings = pd.DataFrame(
        svd.transform(X_train).dot(
            svd.components_[:, X_train.columns.get_indexer(X_test.columns)]
        ),
        index=X_test.index,
        columns=X_test.columns,
    )
    # Returning top n elements
    return pred_ratings.apply(lambda row: row.nlargest(n).index.tolist(), axis=1)


# Function to recommend items for a given user
def recommend_items(user_id, n=10, min_interactions=5):
    # Define weights for the activities - adjust this as needed.
    activity_weight = {
        "view": min_interactions - 2,
        "click": min_interactions - 1,
        "purchase": min_interactions + 1,
    }

    # Get user activity implicit rating
    user_activity_df = load_data(
        UserActivity, {"user_id": user_id}, ["user_id", "item__id", "activity_type"]
    )
    user_activity_df["stars"] = user_activity_df["activity_type"].map(activity_weight)

    # Get explicit ratings from ratings table
    ratings_df = load_data(
        Rating, {"user_id": user_id}, ["user_id", "item__id", "stars"]
    )

    print(ratings_df)

    # Check if ratings_df has more than one unique user
    if ratings_df.empty or ratings_df["user_id"].nunique() <= 1:
        print("Not enough data to make recommendations.")
        return

    # Combine both ratings and user activity dataframes
    ratings_df = (
        pd.concat([ratings_df, user_activity_df])
        .groupby(["user_id", "item__id"])
        .sum()
        .reset_index()
    )

    # Perform Collaborative filtering and update cache.
    item_ids = (
        ratings_df.index.get_level_values("item__id")
        if len(ratings_df) <= 1
        else perform_collaborative_filtering(ratings_df, n)
    )
    update_cache("global", perform_collaborative_filtering(ratings_df, n))

    # Fetch the recommended items
    recommended_items = Item.objects.filter(id__in=item_ids)

    # Get popularity of items
    item_popularity = {
        item["item__id"]: item["avg_rating"]
        for item in Rating.objects.values("item__id").annotate(avg_rating=Avg("stars"))
    }
    # Sort the recommended items by popularity
    recommended_items = sorted(
        recommended_items,
        key=lambda item: item_popularity.get(item.id, 0),
        reverse=True,
    )[:n]
    # check if recommended items are greater than 0
    if len(recommended_items) == 0:
        print("No recommendations found.")
        return []
    # Return the top n recommended items
    return recommended_items
