attributes = {
  email: 'admin@chemotion.net',
  first_name: 'ELN',
  last_name: 'Admin',
  password: 'PleaseChangeYourPassword',
  name_abbreviation: 'ADM',
  type: 'Admin'
}

admin = User.find_or_initialize_by(email: attributes[:email])
admin.assign_attributes(attributes)
admin.confirmed = true
admin.save!

puts "Admin user created: #{admin.email}"
