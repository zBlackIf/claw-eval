<!-- Basic goods card component -->
<template>
  <view class="goods-card" @click="$emit('click', item)">
    <image class="goods-image" :src="item.imageUrl" mode="aspectFill" />
    <view class="goods-info">
      <text class="goods-title">{{ item.title }}</text>
      <view class="price-row">
        <text class="current-price">¥{{ item.price }}</text>
        <text v-if="item.originalPrice" class="original-price">¥{{ item.originalPrice }}</text>
      </view>
      <view class="meta-row">
        <text class="shop-name">{{ item.shopName }}</text>
        <text class="sales">已售{{ item.sales }}件</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import type { GoodsItem } from '../api/goods'

defineProps<{
  item: GoodsItem
}>()

defineEmits<{
  click: [item: GoodsItem]
}>()
</script>

<style lang="scss" scoped>
.goods-card {
  display: flex;
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;

  .goods-image {
    width: 100px;
    height: 100px;
    border-radius: 6px;
    flex-shrink: 0;
  }

  .goods-info {
    flex: 1;
    margin-left: 10px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .goods-title {
    font-size: 14px;
    color: #333;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .price-row {
    display: flex;
    align-items: baseline;
    gap: 6px;
  }

  .current-price {
    font-size: 16px;
    font-weight: bold;
    color: #ff4d4f;
  }

  .original-price {
    font-size: 12px;
    color: #999;
    text-decoration: line-through;
  }

  .meta-row {
    display: flex;
    justify-content: space-between;
  }

  .shop-name, .sales {
    font-size: 12px;
    color: #999;
  }
}
</style>
