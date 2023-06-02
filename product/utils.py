import pandas as pd
from django.db.models import Count
from sklearn.model_selection import train_test_split
from sklearn.decomposition import TruncatedSVD
from product.models import Item
# from numba import jit
from users.models import UserActivity

# Create recommendation function using collaborative filtering
def recommend_items(user_id, n=10):
    # Load the user activity data into a Pandas DataFrame using the Django ORM
    activity = UserActivity.objects.filter(
        user_id=user_id).select_related('item')
    activity = activity.values(
        'user_id', 'item__id', 'item__product_category__name', 'item__product_type__name', 'activity_type')
    activity = activity.annotate(count=Count('activity_type'))
    df = pd.DataFrame.from_records(activity)

    # Preprocess the data by filtering out any irrelevant activity types and aggregating the data by user and item
    df = df[(df['activity_type'] == 'view') | (df['activity_type'] == 'click')]
    df = df.pivot_table(index=['user_id', 'item__id', 'item__product_category__name',
                        'item__product_type__name'], columns='activity_type', values='count')
    df = df.fillna(0)
    df['clicks'] = df['click']
    df['views'] = df['view']
    df = df.drop(columns=['click', 'view'])

    # Check if there is enough data to split into training and test sets
    if len(df) <= 1:
        # If not, return the available items
        item_ids = df.index.get_level_values('item__id')
        recommended_items = Item.objects.filter(
            id__in=item_ids)[:n]
        return recommended_items

    # Split the data into training and test sets
    X_train, X_test = train_test_split(df, test_size=0.2, random_state=42)

    # Use TruncatedSVD to fit a collaborative filtering model on the training data
    svd = TruncatedSVD(n_components=2, random_state=42)
    svd.fit(X_train)

    # Use the model to transform the data and make recommendations based on the latent features
    X_train_decomposed = svd.transform(X_train)
    recommended_items = svd.transform(df)

    # Retrieve the recommended items from the Item model based on their IDs and the category and type of the items
    item_ids = [int(x[0]) for x in recommended_items]
    # print(item_ids)
    recommended_items = Item.objects.filter(
        id__in=item_ids)[:n]

    return recommended_items
