# This file is auto-generated from the current state of the database. Instead
# of editing this file, please use the migrations feature of Active Record to
# incrementally modify your database, and then regenerate this schema definition.
#
# This file is the source Rails uses to define your schema when running `bin/rails
# db:schema:load`. When creating a new database, `bin/rails db:schema:load` tends to
# be faster and is potentially less error prone than running all of your
# migrations from scratch. Old migrations may fail to apply correctly if those
# migrations use external dependencies or application code.
#
# It's strongly recommended that you check this file into your version control system.

ActiveRecord::Schema[7.0].define(version: 2024_03_15_120000) do
  # These are extensions that must be enabled in order to support this database
  enable_extension "hstore"
  enable_extension "pg_trgm"
  enable_extension "plpgsql"
  enable_extension "uuid-ossp"

  create_table "users", id: :integer, force: :cascade do |t|
    t.string "email", default: "", null: false
    t.string "encrypted_password", default: "", null: false
    t.string "first_name", null: false
    t.string "last_name", null: false
    t.string "name_abbreviation", limit: 5
    t.string "type", default: "Person"
    t.boolean "confirmed", default: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["email"], name: "index_users_on_email", unique: true
  end

  create_table "molecules", id: :integer, force: :cascade do |t|
    t.string "inchikey"
    t.string "inchistring"
    t.float "molecular_weight"
    t.text "molfile"
    t.string "sum_formular"
    t.string "iupac_name"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["inchikey"], name: "index_molecules_on_inchikey"
  end

  create_table "samples", id: :integer, force: :cascade do |t|
    t.string "name"
    t.float "target_amount_value"
    t.string "target_amount_unit", default: "mg"
    t.integer "molecule_id"
    t.integer "user_id"
    t.text "description"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["molecule_id"], name: "index_samples_on_molecule_id"
    t.index ["user_id"], name: "index_samples_on_user_id"
  end

  create_table "reactions", id: :integer, force: :cascade do |t|
    t.string "name"
    t.text "description"
    t.string "status", default: "planned"
    t.float "temperature"
    t.string "solvent"
    t.integer "user_id"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
  end

  create_table "collections", id: :integer, force: :cascade do |t|
    t.string "label", null: false
    t.integer "user_id", null: false
    t.boolean "is_shared", default: false
    t.boolean "is_locked", default: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["user_id"], name: "index_collections_on_user_id"
  end

  create_table "collections_samples", id: false, force: :cascade do |t|
    t.integer "collection_id"
    t.integer "sample_id"
    t.index ["collection_id", "sample_id"], name: "idx_collections_samples_unique", unique: true
  end

  create_table "compound_open_data", id: :integer, force: :cascade do |t|
    t.integer "x_id"
    t.integer "x_sample_id"
    t.jsonb "x_data", default: {}
    t.string "x_inchikey"
    t.string "x_sum_formula"
    t.float "x_molecular_weight"
    t.string "x_cas"
    t.boolean "x_released", default: false
    t.datetime "x_created_at"
    t.datetime "x_updated_at"
    t.index ["x_inchikey"], name: "index_compound_open_data_on_x_inchikey"
  end

  # --- Functions that depend on compound_open_data_locals view ---
  # BUG: This function is defined BEFORE the view it depends on.
  # Rails schema:load will fail with PG::UndefinedObject because
  # compound_open_data_locals doesn't exist yet at this point.

  create_function :com_xvial, sql_definition: <<-'SQL'
      CREATE OR REPLACE FUNCTION public.com_xvial(p_allow boolean DEFAULT false)
       RETURNS SETOF compound_open_data_locals
       LANGUAGE plpgsql
      AS $function$
      begin
      	if p_allow IS false then
      		return QUERY SELECT compound_open_data_locals.* FROM compound_open_data_locals;
      	else
      		return QUERY SELECT compound_open_data_locals.* FROM compound_open_data_locals
      		WHERE x_released = true;
      	end if;
      end;
      $function$
  SQL

  create_function :com_xvial_count, sql_definition: <<-'SQL'
      CREATE OR REPLACE FUNCTION public.com_xvial_count(p_allow boolean DEFAULT false)
       RETURNS integer
       LANGUAGE plpgsql
      AS $function$
      declare
        v_count integer;
      begin
      	if p_allow IS false then
      		SELECT count(*) INTO v_count FROM compound_open_data_locals;
      	else
      		SELECT count(*) INTO v_count FROM compound_open_data_locals
      		WHERE x_released = true;
      	end if;
        return v_count;
      end;
      $function$
  SQL

  # --- View definition (referenced by functions above) ---
  # This should come BEFORE the functions that reference it.
  create_view "compound_open_data_locals", sql_definition: <<-'SQL'
      SELECT compound_open_data.x_id,
      compound_open_data.x_sample_id,
      compound_open_data.x_data,
      compound_open_data.x_inchikey,
      compound_open_data.x_sum_formula,
      compound_open_data.x_molecular_weight,
      compound_open_data.x_cas,
      compound_open_data.x_released,
      compound_open_data.x_created_at,
      compound_open_data.x_updated_at
      FROM compound_open_data
      WHERE compound_open_data.x_released = true;
  SQL

  create_table "research_plans", id: :integer, force: :cascade do |t|
    t.string "name"
    t.jsonb "body", default: []
    t.integer "user_id"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
  end

  create_table "attachments", id: :integer, force: :cascade do |t|
    t.string "filename"
    t.string "content_type"
    t.string "identifier"
    t.string "storage", default: "tmp"
    t.integer "attachable_id"
    t.string "attachable_type"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
  end
end
