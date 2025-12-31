import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { AuthContext } from '../App';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useNavigate } from 'react-router-dom';

interface Person {
  id: number;
  name: string;
  category: string;
  expiry?: string;
  contact?: string;
}

interface Event {
  id: number;
  category: string;
  similarity?: number;
  timestamp: string;
}

const Dashboard: React.FC = () => {
  const { token, role, logout } = useContext(AuthContext)!;
  const navigate = useNavigate();
  const [persons, setPersons] = useState<Person[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [form, setForm] = useState({ name: '', category: 'Family' as const, expiry: '', contact: '' });
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) navigate('/login');
    fetchPersons();
    fetchEvents();
  }, [token, navigate]);

  const fetchPersons = async () => {
    try {
      const response = await axios.get('/persons');
      setPersons(response.data);
    } catch (err) {
      console.error('Error fetching persons:', err);
    }
  };

  const fetchEvents = async () => {
    try {
      const response = await axios.get('/events');
      setEvents(response.data);
    } catch (err) {
      console.error('Error fetching events:', err);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) setFile(e.target.files[0]);
  };

  const handleEnroll = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return setMessage('Please select an image file');

    const formData = new FormData();
    formData.append('name', form.name);
    formData.append('category', form.category);
    if (form.expiry) formData.append('expiry', form.expiry);
    if (form.contact) formData.append('contact', form.contact);
    formData.append('file', file);

    setLoading(true);
    setMessage('');
    try {
      const response = await axios.post('/enroll', formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        },
      });
      setMessage(response.data.message);
      setForm({ name: '', category: 'Family', expiry: '', contact: '' });
      setFile(null);
      fetchPersons();
    } catch (err: any) {
      setMessage(`Error: ${err.response?.data?.detail || 'Enrollment failed'}`);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Mock chart data (replace with real events)
  const chartData = events.slice(0, 10).map((event, index) => ({
    name: `Event ${index + 1}`,
    similarity: event.similarity || 0,
    timestamp: new Date(event.timestamp).toLocaleTimeString(),
  }));

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-md p-4 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-800">AUMSecurity Dashboard</h1>
        <div className="flex items-center space-x-4">
          <span className="text-gray-600">Role: {role}</span>
          <button 
            onClick={handleLogout}
            className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="p-6">
        {/* Enrollment Form */}
        <section className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Enroll New Person</h2>
          {message && (
            <div className={`p-3 mb-4 rounded ${message.includes('Error') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
              {message}
            </div>
          )}
          <form onSubmit={handleEnroll} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input
              name="name"
              placeholder="Full Name"
              value={form.name}
              onChange={handleInputChange}
              className="p-2 border rounded-md"
              required
            />
            <select
              name="category"
              value={form.category}
              onChange={handleInputChange}
              className="p-2 border rounded-md"
            >
              <option value="Family">Family</option>
              <option value="Temporary">Temporary</option>
            </select>
            <input
              name="expiry"
              type="date"
              value={form.expiry}
              onChange={handleInputChange}
              className="p-2 border rounded-md"
            />
            <input
              name="contact"
              placeholder="Contact (Phone/Email)"
              value={form.contact}
              onChange={handleInputChange}
              className="p-2 border rounded-md"
            />
            <input
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              className="p-2 border rounded-md col-span-2"
              required
            />
            <button 
              type="submit" 
              disabled={loading}
              className="bg-blue-500 hover:bg-blue-600 text-white p-2 rounded-md col-span-2 disabled:opacity-50"
            >
              {loading ? 'Enrolling...' : 'Enroll Person'}
            </button>
          </form>
        </section>

        {/* Persons List */}
        <section className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Enrolled Persons ({persons.length})</h2>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="bg-gray-200">
                  <th className="border p-2">ID</th>
                  <th className="border p-2">Name</th>
                  <th className="border p-2">Category</th>
                  <th className="border p-2">Expiry</th>
                  <th className="border p-2">Contact</th>
                </tr>
              </thead>
              <tbody>
                {persons.map(person => (
                  <tr key={person.id} className="hover:bg-gray-50">
                    <td className="border p-2">{person.id}</td>
                    <td className="border p-2">{person.name}</td>
                    <td className="border p-2">{person.category}</td>
                    <td className="border p-2">{person.expiry || 'None'}</td>
                    <td className="border p-2">{person.contact || 'None'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Events Chart (Mock) */}
        <section className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Recent Events</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="similarity" stroke="#8884d8" />
            </LineChart>
          </ResponsiveContainer>
        </section>
      </main>
    </div>
  );
};

export default Dashboard;