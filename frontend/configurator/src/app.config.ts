export default defineAppConfig({
  pages: [
    'pages/init/index',
    'pages/message/index',
    'pages/alert/index',
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#fff',
    navigationBarTitleText: '小伴',
    navigationBarTextStyle: 'black',
  },
  tabBar: {
    color: '#999',
    selectedColor: '#0ea5e9',
    list: [
      { pagePath: 'pages/init/index', text: '配置' },
      { pagePath: 'pages/message/index', text: '留话' },
      { pagePath: 'pages/alert/index', text: '通知' },
    ],
  },
})
