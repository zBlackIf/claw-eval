<!--
  Search page - INCOMPLETE STUB
  Requirements:
  - This page needs platform switching tabs and multi-platform search aggregation
  - Currently only has a basic search input, no platform tabs or product list
-->
<template>
  <view class="search-page">
    <view class="search-header" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="search-content">
        <view class="search-input-wrapper">
          <input
            v-model="keyword"
            class="search-input"
            placeholder="搜索商品"
            confirm-type="search"
            @confirm="handleSearch"
          />
        </view>
        <text class="cancel-btn" @click="goBack">取消</text>
      </view>
    </view>

    <view class="search-body" :style="{ paddingTop: headerHeight + 'px' }">
      <!-- TODO: Add platform tabs (全部/淘宝/京东/拼多多) -->
      <!-- TODO: Product list with platform badges -->
      <!-- TODO: Infinite scroll / pull-up load more -->

      <!-- Search history (shown when no search results) -->
      <view v-if="!hasSearched" class="history-section">
        <view class="section-header">
          <text class="section-title">搜索历史</text>
          <text class="clear-btn" @click="clearHistory">清除</text>
        </view>
        <view class="history-tags">
          <text
            v-for="item in searchHistory"
            :key="item"
            class="history-tag"
            @click="searchFromHistory(item)"
          >{{ item }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { searchGoods, type GoodsItem } from '../../api/goods'

const keyword = ref('')
const hasSearched = ref(false)
const searchHistory = ref<string[]>([])
const statusBarHeight = ref(0)
const headerHeight = ref(44)

onMounted(() => {
  // Get status bar height for proper header offset
  if (typeof uni !== 'undefined') {
    const systemInfo = uni.getSystemInfoSync()
    statusBarHeight.value = systemInfo.statusBarHeight || 0
  }
  headerHeight.value = statusBarHeight.value + 44
  // Load search history from storage
  loadHistory()
})

function loadHistory() {
  try {
    const stored = uni.getStorageSync('search_history')
    if (stored) {
      searchHistory.value = JSON.parse(stored)
    }
  } catch (e) {
    searchHistory.value = []
  }
}

function saveHistory(kw: string) {
  if (!kw.trim()) return
  const list = searchHistory.value.filter(i => i !== kw)
  list.unshift(kw)
  if (list.length > 10) list.length = 10
  searchHistory.value = list
  uni.setStorageSync('search_history', JSON.stringify(list))
}

function clearHistory() {
  searchHistory.value = []
  uni.removeStorageSync('search_history')
}

function searchFromHistory(kw: string) {
  keyword.value = kw
  handleSearch()
}

function handleSearch() {
  if (!keyword.value.trim()) return
  saveHistory(keyword.value.trim())
  hasSearched.value = true
  // TODO: Implement actual search with platform switching
}

function goBack() {
  if (typeof uni !== 'undefined') {
    uni.navigateBack()
  }
}
</script>

<style lang="scss" scoped>
.search-page {
  min-height: 100vh;
  background: #f5f5f5;

  .search-header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 100;
    background: #fff;

    .search-content {
      display: flex;
      align-items: center;
      padding: 8px 16px;
    }

    .search-input-wrapper {
      flex: 1;
      height: 36px;
      background: #f5f5f5;
      border-radius: 18px;
      display: flex;
      align-items: center;
      padding: 0 12px;
    }

    .search-input {
      flex: 1;
      height: 36px;
      font-size: 14px;
    }

    .cancel-btn {
      margin-left: 12px;
      font-size: 14px;
      color: #666;
    }
  }

  .search-body {
    padding: 12px;
  }

  .history-section {
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .section-title {
      font-size: 16px;
      font-weight: bold;
    }
    .clear-btn {
      font-size: 13px;
      color: #999;
    }
    .history-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .history-tag {
      padding: 6px 12px;
      background: #fff;
      border-radius: 16px;
      font-size: 13px;
      color: #333;
    }
  }
}
</style>
