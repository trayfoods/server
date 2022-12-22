import pandas as pd
from sklearn.metrics import precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.decomposition import TruncatedSVD
from product.models import Item
from numba import jit
from users.models import UserActivity


# Create recommendation function using collaborative filtering
@jit
def recommend_items(user_id, n=10):
    # Load the user activity data into a Pandas DataFrame using the Django ORM
    activity = UserActivity.objects.filter(user_id=user_id)
    df = pd.DataFrame.from_records(activity.values())

    # Preprocess the data by filtering out any irrelevant activity types and aggregating the data by user and item
    df = df[df['activity_type'].isin(['view', 'click'])]
    df = df.groupby(['user_id', 'item_idx']).sum()

    # Add the category and type of the items as additional features
    df = df.reset_index()
    df['item_idx'] = df['item'].apply(lambda x: x.id)
    df['product_category__name'] = df['item'].apply(
        lambda x: x.product_category__name)
    df['product_type__name'] = df['item'].apply(lambda x: x.product_type__name)
    df = df.groupby(
        ['user_id', 'item_idx', 'product_category__name', 'product_type__name']).sum()

    # Split the data into training and test sets
    X_train, X_test = train_test_split(df, test_size=0.2, random_state=42)

    # Use TruncatedSVD to fit a collaborative filtering model on the training data
    svd = TruncatedSVD(n_components=10, random_state=42)
    X_train_decomposed = svd.fit_transform(X_train)

    # Use the model to make recommendations for the user by predicting their interactions with items in the test set
    recommendations = svd.predict(X_test)

    # Evaluate the performance of the model using precision or recall
    precision = precision_score(X_test, recommendations)
    recall = recall_score(X_test, recommendations)

    # Use the model to make recommendations for the user based on their past interactions with items
    recommended_items = svd.predict(df)

    # Retrieve the recommended items from the Item model based on their IDs and the category and type of the items
    recommended_items = recommended_items[:n]
    recommended_items = Item.objects.filter(
        id__in=recommended_items, product_category__name=df['product_category__name'], product_type__name=df['product_type__name'])

    return recommended_items
