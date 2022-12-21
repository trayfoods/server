import pandas as pd
from django.db.models import Count
from django.db.models import F
from django.utils import timezone
from sklearn.neighbors import NearestNeighbors
from product.models import Item

from users.models import UserActivity


# Create recommendation function using collaborative filtering
def recommend_items(user_id, region=None, calories=0, num_recommendations=100):
    # Get user activity data
    items = Item.objects.all().distinct().values()
    items = pd.DataFrame(items)
    items = user_data.rename(columns={'id': 'item_id'})

    # Get user activity data
    user_data = UserActivity.objects.filter(user_id=user_id).values('item__id', 'timestamp', 'activity_type')
    user_data = pd.DataFrame(user_data)
    user_data = user_data.rename(columns={'item__id': 'item_id'})

    # Calculate the number of views and clicks for each item
    item_views = user_data[user_data['activity_type'] == 'view'].values(
        'item_id').annotate(views=Count('item_id'))
    item_clicks = user_data[user_data['activity_type'] == 'click'].values(
        'item_id').annotate(clicks=Count('item_id'))

    # Merge view and click data for each item
    item_data = pd.merge(item_views, item_clicks, on='item_id', how='outer')
    item_data = item_data.fillna(0)

    # Get last item viewed and clicked by the user
    last_viewed = user_data[user_data['activity_type'] == 'view'].last()
    last_clicked = user_data[user_data['activity_type'] == 'click'].last()

    # Calculate a score for each item based on views, clicks, and last viewed/clicked status
    item_data['score'] = item_data['product_views'] * 0.5 + item_data['product_clicks'] * 2
    if last_viewed:
        # Give additional weight if the last viewed item is recent
        time_delta = timezone.now() - last_viewed.timestamp
        if time_delta.days < 7:
            item_data.loc[item_data['item_id'] ==
                          last_viewed.item_id, 'score'] += 0.5
    if last_clicked:
        # Give additional weight if the last clicked item is recent
        time_delta = timezone.now() - last_clicked.timestamp
        if time_delta.days < 7:
            item_data.loc[item_data['item_id'] ==
                          last_clicked.item_id, 'score'] += 0.5

    # Scale scores to be between 0 and 1
    item_data['score'] = (item_data['score'] - item_data['score'].min()) / \
        (item_data['score'].max() - item_data['score'].min())

    # Merge item data with item metadata
    item_data = pd.merge(item_data, items, on='item_id')

    data_filtered = item_data
    # Filter data to only include items in the specified region
    if region:
        data_filtered = item_data[item_data['region'] == region]

    # Fit nearest neighbors model on data
    model_knn = NearestNeighbors(
        metric='cosine', algorithm='brute', n_neighbors=20, n_jobs=-1)
    model_knn.fit(data_filtered[['score', 'calories']])

    # Get distances and indices of nearest neighbors
    distances, indices = model_knn.kneighbors(
        [[0, calories]], n_neighbors=num_recommendations+1)

    # Get list of recommended item IDs
    item_ids = []
    for i in range(1, len(distances.flatten())):
        item_id = data_filtered.iloc[indices.flatten()[i], 0]
        item_ids.append(item_id)

    # Get recommended items from Item model
    recommended_items = Item.objects.filter(id__in=item_ids)

    return recommended_items
