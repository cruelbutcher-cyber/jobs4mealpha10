import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random

# Country Priority Weights
COUNTRY_WEIGHTS = {
    'USA': 1.5,
    'Canada': 1.4,
    'Germany': 1.3,
    'Australia': 1.3,
    'Philippines': 0.7,
    'India': 0.6,
    'Japan': 0.6
}

# Job Sources (removed GitHub Jobs as it's deprecated)
JOB_SOURCES = {
    'WeWorkRemotely': 'https://weworkremotely.com/remote-jobs/search?term=',
    'RemoteOK': 'https://remoteok.com/remote-'
}

def analyze_skills(job_position):
    """Extract skills from job position"""
    # Common skills mapping based on job titles
    skills_mapping = {
        'developer': ['python', 'javascript', 'html', 'css', 'react', 'node.js', 'sql', 'git'],
        'data': ['python', 'sql', 'pandas', 'numpy', 'statistics', 'machine learning', 'data visualization'],
        'analyst': ['sql', 'excel', 'data analysis', 'statistics', 'tableau', 'powerbi'],
        'designer': ['ui', 'ux', 'adobe', 'figma', 'sketch', 'wireframing', 'prototype'],
        'manager': ['leadership', 'project management', 'agile', 'scrum', 'communication'],
        'marketing': ['seo', 'social media', 'content creation', 'analytics', 'email marketing'],
        'customer': ['communication', 'problem solving', 'patience', 'crm', 'conflict resolution'],
        'sales': ['negotiation', 'crm', 'prospecting', 'cold calling', 'relationship building'],
        'support': ['troubleshooting', 'communication', 'patience', 'ticketing systems', 'problem solving']
    }
    
    # Convert job position to lowercase for matching
    job_position_lower = job_position.lower()
    
    # Find matching skills
    identified_skills = []
    for key, skills in skills_mapping.items():
        if key in job_position_lower:
            identified_skills.extend(skills)
    
    # If no skills were found, return default general skills
    if not identified_skills:
        return ['communication', 'teamwork', 'problem solving', 'adaptability', 'time management']
    
    return list(set(identified_skills))  # Remove duplicates

def scrape_weworkremotely(query):
    """Scrape WeWorkRemotely for jobs"""
    jobs = []
    try:
        # Add the query to the URL
        url = JOB_SOURCES['WeWorkRemotely'] + query.replace(' ', '+')
        
        # Add a User-Agent header to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Send a request to the URL
        response = requests.get(url, headers=headers, timeout=10)
        
        # Check if the request was successful
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all job listings
            job_elements = soup.select('li.feature')
            
            for job in job_elements:
                title_element = job.select_one('span.title')
                company_element = job.select_one('span.company')
                location_element = job.select_one('span.region')
                link_element = job.select_one('a')
                
                if title_element and company_element:
                    title = title_element.text.strip()
                    company = company_element.text.strip()
                    location = location_element.text.strip() if location_element else "Remote"
                    link = "https://weworkremotely.com" + link_element['href'] if link_element else ""
                    
                    jobs.append({
                        'title': title,
                        'company': company,
                        'location': location,
                        'url': link,
                        'source': 'WeWorkRemotely'
                    })
            
            st.success(f"Found {len(jobs)} jobs on WeWorkRemotely")
        else:
            st.warning(f"WeWorkRemotely returned status code: {response.status_code}")
            
    except Exception as e:
        st.error(f"WeWorkRemotely scraping failed: {str(e)}")
    
    return jobs

def scrape_remoteok(query):
    """Scrape RemoteOK for jobs"""
    jobs = []
    try:
        # Format the query for RemoteOK
        url = JOB_SOURCES['RemoteOK'] + query.replace(' ', '-')
        
        # Add a User-Agent header to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Add a delay to avoid rate limiting
        time.sleep(2)
        
        # Send a request to the URL
        response = requests.get(url, headers=headers, timeout=10)
        
        # Check if the request was successful
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all job listings (RemoteOK uses <tr> with class 'job')
            job_elements = soup.select('tr.job')
            
            for job in job_elements:
                title_element = job.select_one('h2')
                company_element = job.select_one('h3')
                location_element = job.select_one('div.location')
                
                # RemoteOK uses data attributes for the job URL
                job_id = job.get('data-id')
                
                if title_element and company_element:
                    title = title_element.text.strip()
                    company = company_element.text.strip()
                    location = location_element.text.strip() if location_element else "Remote"
                    link = f"https://remoteok.com/remote-jobs/{job_id}" if job_id else ""
                    
                    jobs.append({
                        'title': title,
                        'company': company,
                        'location': location,
                        'url': link,
                        'source': 'RemoteOK'
                    })
            
            st.success(f"Found {len(jobs)} jobs on RemoteOK")
        else:
            st.warning(f"RemoteOK returned status code: {response.status_code}")
            
    except Exception as e:
        st.error(f"RemoteOK scraping failed: {str(e)}")
    
    return jobs

def get_country_priority(location):
    """Get priority score based on country"""
    for country, weight in COUNTRY_WEIGHTS.items():
        if country.lower() in location.lower():
            return weight
    return 1.0  # Default weight

def calculate_job_match(job, skills):
    """Calculate job match score"""
    job_title = job['title'].lower()
    job_description = job.get('description', '').lower()
    
    # Calculate skill match score
    skill_count = 0
    for skill in skills:
        if skill.lower() in job_title or skill.lower() in job_description:
            skill_count += 1
    
    # Calculate country priority score
    country_score = get_country_priority(job['location'])
    
    # Calculate final match score (skills + country priority)
    match_score = (skill_count / max(1, len(skills))) * country_score
    
    return match_score

def main():
    st.title("📊 Job Scout AI")
    st.write("Find the best remote jobs matching your skills and preferences.")
    
    with st.container():
        st.markdown("### What job are you looking for?")
        job_position = st.text_input("Enter your desired job position (e.g., Python Developer, Data Analyst, Customer Service)", "")
        
        st.markdown("### Additional Preferences")
        col1, col2 = st.columns(2)
        
        with col1:
            preferred_countries = st.multiselect(
                "Preferred Countries (Optional)",
                options=list(COUNTRY_WEIGHTS.keys()),
                default=["USA", "Canada"]
            )
        
        with col2:
            min_match_score = st.slider(
                "Minimum Match Score",
                min_value=0.0,
                max_value=1.0,
                value=0.3,
                step=0.1
            )
    
    # Process job search when the button is clicked
    if st.button("Find Jobs") and job_position:
        with st.spinner("Searching for jobs... This may take a moment."):
            # Identify skills from job position
            skills = analyze_skills(job_position)
            
            # Display identified skills
            st.write("### Skills Identified")
            skills_html = ', '.join([f"<span style='background-color: #e6f3ff; padding: 3px 8px; margin: 0 5px 5px 0; border-radius: 10px; display: inline-block;'>{skill}</span>" for skill in skills])
            st.markdown(f"<div style='margin-bottom: 20px;'>{skills_html}</div>", unsafe_allow_html=True)
            
            # Search for jobs
            all_jobs = []
            
            # Scrape WeWorkRemotely
            wwr_jobs = scrape_weworkremotely(job_position)
            all_jobs.extend(wwr_jobs)
            
            # Scrape RemoteOK
            remoteok_jobs = scrape_remoteok(job_position)
            all_jobs.extend(remoteok_jobs)
            
            # Calculate match scores for all jobs
            for job in all_jobs:
                job['match_score'] = calculate_job_match(job, skills)
            
            # Apply country filter if selected
            if preferred_countries:
                filtered_jobs = [
                    job for job in all_jobs 
                    if any(country.lower() in job['location'].lower() for country in preferred_countries)
                    or "remote" in job['location'].lower()
                ]
            else:
                filtered_jobs = all_jobs
            
            # Apply minimum match score filter
            filtered_jobs = [job for job in filtered_jobs if job['match_score'] >= min_match_score]
            
            # Sort by match score
            filtered_jobs.sort(key=lambda x: x['match_score'], reverse=True)
            
            # Convert to DataFrame for display
            if filtered_jobs:
                df = pd.DataFrame(filtered_jobs)
                
                # Format the match score as a percentage
                df['match_score'] = df['match_score'].apply(lambda x: f"{x:.0%}")
                
                # Rename columns for display
                df = df.rename(columns={
                    'title': 'Job Title',
                    'company': 'Company',
                    'location': 'Location',
                    'url': 'URL',
                    'source': 'Source',
                    'match_score': 'Match Score'
                })
                
                # Create clickable links
                df['URL'] = df['URL'].apply(lambda x: f'<a href="{x}" target="_blank">Apply</a>')
                
                # Display the dataframe
                st.write(f"### Found {len(filtered_jobs)} Matching Jobs")
                st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)
                
                # Add download option
                st.download_button(
                    "Download Results as CSV",
                    df.to_csv(index=False).encode('utf-8'),
                    "job_matches.csv",
                    "text/csv",
                    key='download-csv'
                )
            else:
                st.warning("No matching jobs found. Try adjusting your search criteria.")

if __name__ == "__main__":
    main()
