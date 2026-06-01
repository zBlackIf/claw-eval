class RdChartsController < ApplicationController
  before_action :find_project
  before_action :authorize

  def index
    @issues = @project.issues
    @total = @issues.count
    @open = @issues.open.count
    @closed = @total - @open
    @overdue = @issues.open.where("due_date < ?", Date.today).count

    # Dimension data
    @by_tracker = @issues.group(:tracker).count
    @by_status = @issues.group(:status).count
    @by_priority = @issues.joins(:priority).group("enumerations.name").count
    @by_assignee = @issues.joins(:assigned_to).group("users.login").count

    # Trend data (last 12 weeks)
    @weekly_created = @issues.where("created_on >= ?", 12.weeks.ago)
                             .group_by_week(:created_on).count
    @weekly_closed = @issues.where("closed_on >= ?", 12.weeks.ago)
                            .where.not(closed_on: nil)
                            .group_by_week(:closed_on).count
  end

  private

  def find_project
    @project = Project.find(params[:project_id])
  rescue ActiveRecord::RecordNotFound
    render_404
  end
end
