import { useState, useMemo } from 'react';
import axios from 'axios';
import { Search, ChevronUp, ChevronDown, ExternalLink } from 'lucide-react';
import './App.css';

function App() {
  const [query, setQuery] = useState('');
  const [minFunding, setMinFunding] = useState(0);
  const [status, setStatus] = useState('Active');
  const [limit, setLimit] = useState(100);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sortConfig, setSortConfig] = useState({ key: 'total_funding', direction: 'desc' });

  const handleSearch = async (e) => {
    e.preventDefault();
    // Removed the "if (!query) return" line so you can hit Search with an empty box

    setLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/search', {
        query,
        min_funding: minFunding,
        status,
        limit: limit
      });
      
      // Clean up company names by removing anything in brackets [url]
      const cleanedResults = response.data.results.map(company => ({
        ...company,
        company_name: company.company_name ? company.company_name.replace(/\s*\[.*?\]/g, '').trim() : 'Unknown'
      }));
      
      setResults(cleanedResults);
    } catch (error) {
      console.error('Search failed:', error);
      alert('Search failed. Make sure the Python backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    if (!amount || amount === 0) return '-';
    if (amount >= 1e9) return `$${(amount / 1e9).toFixed(1)}B`;
    if (amount >= 1e6) return `$${(amount / 1e6).toFixed(1)}M`;
    if (amount >= 1e3) return `$${(amount / 1e3).toFixed(0)}K`;
    return `$${amount}`;
  };

  const getLinkLabel = (url) => {
    const lowerUrl = url.toLowerCase();
    if (lowerUrl.includes('instagram.com')) return 'Instagram';
    if (lowerUrl.includes('twitter.com') || lowerUrl.includes('x.com')) return 'X (Twitter)';
    if (lowerUrl.includes('linkedin.com')) return 'LinkedIn';
    if (lowerUrl.includes('facebook.com')) return 'Facebook';
    if (lowerUrl.includes('crunchbase.com')) return 'Crunchbase';
    if (lowerUrl.includes('github.com')) return 'GitHub';
    if (lowerUrl.includes('youtube.com')) return 'YouTube';
    if (lowerUrl.includes('aventure.vc')) return 'Aventure.vc';
    return 'Website';
  };

  const renderLinks = (linksStr) => {
    if (!linksStr) return '-';
    const matches = [...linksStr.matchAll(/\[(.*?)\]/g)].map(m => m[1]);
    
    if (matches.length > 0) {
      return (
        <div className="links-cell">
          {matches.map((url, i) => (
            <a key={i} href={url} target="_blank" rel="noreferrer" title={url}>
              <ExternalLink size={14} /> {getLinkLabel(url)}
            </a>
          ))}
        </div>
      );
    }
    return <a href={linksStr} target="_blank" rel="noreferrer"><ExternalLink size={14} /> {getLinkLabel(linksStr)}</a>;
  };

  const requestSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const sortedResults = useMemo(() => {
    let sortableItems = [...results];
    if (sortConfig !== null) {
      sortableItems.sort((a, b) => {
        if (a[sortConfig.key] < b[sortConfig.key]) {
          return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (a[sortConfig.key] > b[sortConfig.key]) {
          return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }
    return sortableItems;
  }, [results, sortConfig]);

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return <ChevronUp className="sort-icon inactive" size={14} />;
    return sortConfig.direction === 'asc' ? <ChevronUp className="sort-icon" size={14} /> : <ChevronDown className="sort-icon" size={14} />;
  };

  return (
    <div className="container">
      <header>
        <h1>Company Vector Search</h1>
        <p>Semantic search powered by pgvector & BAAI/bge-large</p>
      </header>

      <div className="search-container">
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-bar">
            <Search className="search-icon" size={20} />
            <input
              type="text"
              placeholder='e.g. "Find me AI dev tools for healthcare..."'
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={loading}
            />
            <button type="submit" disabled={loading}>
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>

          <div className="filters">
            <div className="filter-group">
              <label>Min Funding:</label>
              <select value={minFunding} onChange={(e) => setMinFunding(Number(e.target.value))}>
                <option value={0}>Any</option>
                <option value={1000000}>$1 Million+</option>
                <option value={10000000}>$10 Million+</option>
                <option value={50000000}>$50 Million+</option>
                <option value={100000000}>$100 Million+</option>
              </select>
            </div>
            
            <div className="filter-group">
              <label>Status:</label>
              <select value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="">Any</option>
                <option value="Active">Active</option>
                <option value="Acquired">Acquired</option>
                <option value="Closed">Closed</option>
              </select>
            </div>

            <div className="filter-group">
              <label>Max Results:</label>
              <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={500}>500</option>
                <option value={1000}>1000</option>
              </select>
            </div>
          </div>
        </form>
      </div>

      {loading && <div className="loading-message">Fetching data... Please wait.</div>}

      <div className="table-container">
        <table className="results-table">
          <thead>
            <tr>
              <th onClick={() => requestSort('company_name')}>Company <SortIcon columnKey="company_name" /></th>
              <th>Summary</th>
              <th onClick={() => requestSort('stage')}>Stage <SortIcon columnKey="stage" /></th>
              <th onClick={() => requestSort('hq')}>HQ <SortIcon columnKey="hq" /></th>
              <th onClick={() => requestSort('year_founded')}>Year <SortIcon columnKey="year_founded" /></th>
              <th onClick={() => requestSort('latest_funding')}>Latest Funding <SortIcon columnKey="latest_funding" /></th>
              <th onClick={() => requestSort('total_funding')}>Total Funding <SortIcon columnKey="total_funding" /></th>
              <th onClick={() => requestSort('employee_count')}>Employees <SortIcon columnKey="employee_count" /></th>
              <th onClick={() => requestSort('status')}>Status <SortIcon columnKey="status" /></th>
              <th>Links</th>
            </tr>
          </thead>
          <tbody>
            {sortedResults.map((company, index) => (
              <tr key={index}>
                <td className="fw-bold">{company.company_name}</td>
                <td className="summary-cell">{company.summary}</td>
                <td>{company.stage}</td>
                <td>{company.hq}</td>
                <td>{company.year_founded > 0 ? company.year_founded : '-'}</td>
                <td>{formatCurrency(company.latest_funding)}</td>
                <td className="fw-bold">{formatCurrency(company.total_funding)}</td>
                <td>{company.employee_count > 0 ? company.employee_count.toLocaleString() : '-'}</td>
                <td>
                  <span className={`status-badge ${company.status.toLowerCase()}`}>
                    {company.status}
                  </span>
                </td>
                <td>{renderLinks(company.links)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {results.length === 0 && !loading && query && (
          <div className="no-results">No matches found. Try adjusting filters.</div>
        )}
      </div>
    </div>
  );
}

export default App;