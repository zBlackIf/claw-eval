Redmine::Plugin.register :rd_charts do
  name 'Rd Charts'
  author 'DevTeam'
  description 'Project statistics charts plugin for Redmine'
  version '0.2.0'
  url 'https://example.com/rd_charts'

  menu :project_menu, :rd_charts, { controller: 'rd_charts', action: 'index' },
       caption: :rd_charts_title, after: :activity, param: :project_id
end
