# adapted from https://gist.github.com/servel333/47f6cca9e51497aeefab

## db/seeds.rb
['all', Rails.env].each do |seed|
  seed_file = Rails.root.join('db', 'seeds', "#{seed}.rb")
  if File.exists?(seed_file)
    puts "*** Loading #{seed} seed data"
    load seed_file
  end
end
