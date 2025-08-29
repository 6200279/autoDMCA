import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Calendar, Clock, User, ArrowLeft, Share2, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { cn } from '@/lib/utils';

// Blog post interface
interface BlogPost {
  id: string;
  title: string;
  slug: string;
  excerpt: string;
  content: string;
  author: {
    name: string;
    avatar?: string;
    bio: string;
  };
  publishedAt: string;
  readTime: number;
  category: string;
  tags: string[];
  featured: boolean;
  image?: string;
}

// Mock blog data - in a real app, this would come from an API
const blogPosts: BlogPost[] = [
  {
    id: '1',
    title: 'How OnlyFans Creators Are Losing $50,000+ Per Year to Content Theft',
    slug: 'onlyfans-creators-losing-money-content-theft',
    excerpt: 'Content piracy is costing creators more than they realize. Here\'s how to calculate your actual losses and what you can do about it.',
    content: `
# The Hidden Cost of Content Theft

Content theft is more than just an annoyance—it's a direct attack on your revenue. Recent studies show that OnlyFans creators lose an average of $50,000 per year to content piracy.

## The Real Numbers

When your content gets stolen and reposted on free sites, you're not just losing that one sale. You're losing:

- **Potential subscribers** who found your content for free
- **Brand reputation** when low-quality reposts represent your work  
- **Search engine ranking** when duplicate content dilutes your SEO
- **Time and energy** dealing with takedown requests

## Case Study: Sarah's Story

Sarah, an OnlyFans creator with 10,000 followers, discovered her content on 47 different piracy sites. After implementing automated DMCA protection:

- **Revenue increased 73%** within 3 months
- **New subscriber rate doubled** 
- **Time spent on takedowns reduced to zero**

## Taking Action

The solution isn't to stop creating—it's to protect what you create. Automated DMCA protection removes the manual work while ensuring your content stays exclusive to paying subscribers.

*Ready to protect your revenue? Start your free trial today.*
    `,
    author: {
      name: 'Alex Rivera',
      bio: 'Digital Rights Expert & Content Creator Advocate'
    },
    publishedAt: '2024-03-15',
    readTime: 8,
    category: 'Creator Economics',
    tags: ['OnlyFans', 'Revenue Protection', 'DMCA'],
    featured: true,
    image: 'https://images.unsplash.com/photo-1553028826-f4804a6dba3b?w=800&h=400&fit=crop'
  },
  {
    id: '2',
    title: 'DMCA Takedown Success Rates: What Actually Works in 2024',
    slug: 'dmca-takedown-success-rates-2024',
    excerpt: 'Not all DMCA notices are created equal. Learn which strategies achieve 94%+ success rates vs. the 60% industry average.',
    content: `
# The Science Behind Successful DMCA Takedowns

Most DIY DMCA notices fail. Here's why professional services achieve 94%+ success rates while individual creators struggle with 60%.

## What Makes the Difference

**Professional DMCA services succeed because they:**

1. **Use registered agents** - hosting providers take these more seriously
2. **Follow precise legal formatting** - technical compliance matters
3. **Provide proper documentation** - evidence packages that can't be disputed
4. **Handle escalations professionally** - know when and how to escalate

## Common Mistakes That Kill Success Rates

- Vague infringement descriptions
- Missing contact information
- Incorrect legal formatting
- No follow-up strategy
- Emotional language instead of legal language

## The Anonymous Advantage

Many creators avoid sending takedowns because they don't want their personal information exposed. Professional DMCA agents solve this by:

- Keeping your identity completely private
- Using their registered legal credentials
- Handling all communication on your behalf
- Providing legal protection if challenges arise

*Want 94%+ success rates? Try professional DMCA protection free for 14 days.*
    `,
    author: {
      name: 'Maria Santos',
      bio: 'Legal Technology Specialist'
    },
    publishedAt: '2024-03-12',
    readTime: 6,
    category: 'Legal Guide',
    tags: ['DMCA', 'Legal Process', 'Success Rates'],
    featured: true,
    image: 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=800&h=400&fit=crop'
  },
  {
    id: '3',
    title: 'AI vs. Human: Why Automated Content Detection Finds 300% More Theft',
    slug: 'ai-content-detection-vs-human-monitoring',
    excerpt: 'Human monitoring misses 70% of content theft. Here\'s how AI-powered detection revolutionizes creator protection.',
    content: `
# The AI Revolution in Content Protection

Trying to manually monitor the internet for your stolen content is like looking for needles in an ever-growing haystack. AI changes everything.

## The Numbers Don't Lie

**Human monitoring finds:**
- 2-5 instances per week (if you're lucky)
- Only obvious, exact matches
- Limited to platforms you know about

**AI monitoring finds:**
- 50+ instances per week on average
- Partial matches and modified content
- Content across 10M+ websites automatically

## How AI Sees What Humans Miss

AI doesn't get tired, doesn't need breaks, and can:

- Scan millions of images simultaneously
- Detect content even when cropped, filtered, or watermarked
- Identify partial matches and derivative works
- Monitor new platforms as they emerge
- Work 24/7 without supervision

## Real Creator Results

"I thought I was doing pretty well catching thieves manually. Then AI found 127 more instances I'd completely missed. My revenue jumped 45% in the first month." - Jamie K., Content Creator

## The Future is Automated

Manual content monitoring is becoming obsolete. Creators who embrace AI protection are seeing:

- **3x more theft detected**
- **5x faster takedown response**  
- **Zero time spent on manual monitoring**
- **Significantly higher revenue retention**

*Experience AI-powered protection with a 14-day free trial.*
    `,
    author: {
      name: 'Dr. James Chen',
      bio: 'AI Research Director'
    },
    publishedAt: '2024-03-08',
    readTime: 7,
    category: 'Technology',
    tags: ['AI', 'Detection Technology', 'Automation'],
    featured: false,
    image: 'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800&h=400&fit=crop'
  },
  {
    id: '4',
    title: 'Platform-by-Platform: Where Your Content Gets Stolen Most',
    slug: 'content-theft-platforms-analysis-2024',
    excerpt: 'A comprehensive analysis of where stolen content appears most frequently and how to protect against each platform type.',
    content: `
# The Content Theft Landscape: 2024 Analysis

Not all platforms pose the same risk. Here's where your content is most likely to be stolen and what to do about it.

## High-Risk Platforms (80% of theft)

### 1. Tube Sites & Aggregators
- **Risk Level:** Extreme
- **Typical Response Time:** 5-14 days
- **Success Rate:** 85-95% with proper DMCA process

### 2. Social Media Platforms  
- **Risk Level:** High
- **Typical Response Time:** 1-7 days
- **Success Rate:** 90%+ (excellent internal processes)

### 3. File Sharing Sites
- **Risk Level:** High
- **Typical Response Time:** 7-21 days  
- **Success Rate:** 70-90% (varies by host)

## Medium-Risk Platforms (15% of theft)

### Forums & Image Boards
- **Risk Level:** Medium
- **Response varies:** Highly dependent on moderation

### Personal Blogs & Websites
- **Risk Level:** Medium  
- **Response varies:** 60-95% depending on hosting provider

## The Protection Strategy

**For high-risk platforms:** Automated monitoring is essential—manual checking can't keep up with the volume.

**For medium-risk platforms:** Weekly automated scans catch most instances before they spread.

**For all platforms:** Professional DMCA services achieve consistently higher success rates than DIY approaches.

## Case Study: Multi-Platform Protection

Creator "Ashley" implemented comprehensive monitoring across all platform types:

- **Month 1:** Found 234 instances across 67 platforms  
- **Month 3:** 89% of content successfully removed
- **Month 6:** Revenue increased 52% with automated protection

*Protect your content across all platforms with comprehensive monitoring.*
    `,
    author: {
      name: 'Sophie Martinez',
      bio: 'Digital Security Researcher'
    },
    publishedAt: '2024-03-05',
    readTime: 9,
    category: 'Platform Analysis',
    tags: ['Platform Security', 'Risk Assessment', 'Content Monitoring'],
    featured: false,
    image: 'https://images.unsplash.com/photo-1611224923853-80b023f02d71?w=800&h=400&fit=crop'
  }
];

const categories = ['All', 'Creator Economics', 'Legal Guide', 'Technology', 'Platform Analysis'];

interface BlogPageProps {
  className?: string;
}

export const BlogPage: React.FC<BlogPageProps> = ({ className }) => {
  const { slug } = useParams<{ slug?: string }>();
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [currentPost, setCurrentPost] = useState<BlogPost | null>(null);

  // If slug is provided, we're viewing a single post
  useEffect(() => {
    if (slug) {
      const post = blogPosts.find(p => p.slug === slug);
      setCurrentPost(post || null);
    } else {
      setCurrentPost(null);
    }
  }, [slug]);

  // Filter posts by category
  const filteredPosts = selectedCategory === 'All' 
    ? blogPosts 
    : blogPosts.filter(post => post.category === selectedCategory);

  const featuredPosts = blogPosts.filter(post => post.featured);

  // Single post view
  if (currentPost) {
    return (
      <>
        <Helmet>
          <title>{currentPost.title} | ShieldMyContent Blog</title>
          <meta name="description" content={currentPost.excerpt} />
          <meta property="og:title" content={currentPost.title} />
          <meta property="og:description" content={currentPost.excerpt} />
          <meta property="og:type" content="article" />
          {currentPost.image && <meta property="og:image" content={currentPost.image} />}
          <script type="application/ld+json">
            {JSON.stringify({
              "@context": "https://schema.org",
              "@type": "Article",
              "headline": currentPost.title,
              "description": currentPost.excerpt,
              "author": {
                "@type": "Person",
                "name": currentPost.author.name
              },
              "datePublished": currentPost.publishedAt,
              "publisher": {
                "@type": "Organization",
                "name": "ShieldMyContent"
              }
            })}
          </script>
        </Helmet>

        <div className="min-h-screen bg-background">
          
          <main className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
            {/* Back to Blog */}
            <Link to="/blog" className="inline-flex items-center text-sm text-muted-foreground hover:text-primary mb-8">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Blog
            </Link>

            <article className="max-w-4xl mx-auto">
              {/* Article Header */}
              <header className="mb-12">
                <div className="flex items-center gap-2 mb-4">
                  <Badge variant="secondary">{currentPost.category}</Badge>
                  {currentPost.tags.map(tag => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>

                <h1 className="text-4xl sm:text-5xl font-bold text-slate-900 mb-6 leading-tight">
                  {currentPost.title}
                </h1>

                <div className="flex items-center gap-6 text-sm text-muted-foreground mb-8">
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4" />
                    <span>{currentPost.author.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4" />
                    <span>{new Date(currentPost.publishedAt).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    <span>{currentPost.readTime} min read</span>
                  </div>
                </div>

                {currentPost.image && (
                  <img 
                    src={currentPost.image} 
                    alt={currentPost.title}
                    className="w-full h-64 sm:h-80 object-cover rounded-xl mb-8"
                  />
                )}
              </header>

              {/* Article Content */}
              <div className="prose prose-lg max-w-none">
                <div dangerouslySetInnerHTML={{ __html: currentPost.content.split('\n').map(line => {
                  if (line.startsWith('# ')) return `<h1 class="text-3xl font-bold mb-6 text-slate-900">${line.slice(2)}</h1>`;
                  if (line.startsWith('## ')) return `<h2 class="text-2xl font-semibold mb-4 mt-8 text-slate-900">${line.slice(3)}</h2>`;
                  if (line.startsWith('### ')) return `<h3 class="text-xl font-semibold mb-3 mt-6 text-slate-900">${line.slice(4)}</h3>`;
                  if (line.startsWith('**') && line.endsWith('**')) return `<p class="font-semibold mb-4 text-slate-800">${line.slice(2, -2)}</p>`;
                  if (line.startsWith('- **') || line.startsWith('1. **')) {
                    const match = line.match(/^(\d+\.\s|\-\s)\*\*(.*?)\*\*(.*)/);
                    if (match) return `<li class="mb-2"><strong>${match[2]}</strong>${match[3]}</li>`;
                  }
                  if (line.startsWith('- ') || line.startsWith('1. ')) return `<li class="mb-2">${line.slice(2)}</li>`;
                  if (line.startsWith('*') && line.endsWith('*')) return `<p class="italic text-blue-600 font-medium text-center py-4">${line.slice(1, -1)}</p>`;
                  if (line.trim() === '') return '<br>';
                  return `<p class="mb-4 leading-relaxed text-slate-700">${line}</p>`;
                }).join('') }} />
              </div>

              {/* Author Bio */}
              <div className="mt-12 p-6 bg-slate-50 rounded-xl">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold text-xl">
                    {currentPost.author.name.charAt(0)}
                  </div>
                  <div>
                    <h4 className="font-semibold text-lg">{currentPost.author.name}</h4>
                    <p className="text-muted-foreground">{currentPost.author.bio}</p>
                  </div>
                </div>
              </div>

              {/* Related Posts */}
              <div className="mt-16">
                <h3 className="text-2xl font-bold mb-8">Related Articles</h3>
                <div className="grid md:grid-cols-2 gap-6">
                  {blogPosts.filter(post => post.id !== currentPost.id && (
                    post.category === currentPost.category || 
                    post.tags.some(tag => currentPost.tags.includes(tag))
                  )).slice(0, 2).map(post => (
                    <Card key={post.id} className="hover:shadow-lg transition-shadow">
                      <Link to={`/blog/${post.slug}`}>
                        <CardContent className="p-6">
                          <h4 className="font-semibold mb-2 hover:text-blue-600">{post.title}</h4>
                          <p className="text-muted-foreground text-sm line-clamp-3">{post.excerpt}</p>
                          <div className="flex items-center gap-4 mt-4 text-xs text-muted-foreground">
                            <span>{new Date(post.publishedAt).toLocaleDateString()}</span>
                            <span>{post.readTime} min read</span>
                          </div>
                        </CardContent>
                      </Link>
                    </Card>
                  ))}
                </div>
              </div>
            </article>
          </main>
        </div>
      </>
    );
  }

  // Blog listing view
  return (
    <>
      <Helmet>
        <title>Blog - Content Protection Insights | ShieldMyContent</title>
        <meta name="description" content="Expert insights on content protection, DMCA takedowns, and creator revenue security. Learn how to protect your digital content from theft." />
        <meta property="og:title" content="ShieldMyContent Blog - Content Protection Insights" />
        <meta property="og:description" content="Expert insights on content protection, DMCA takedowns, and creator revenue security." />
        <meta property="og:type" content="website" />
      </Helmet>

      <div className="min-h-screen bg-background">
        
        <main>
          {/* Blog Hero Section */}
          <section className="bg-gradient-to-br from-blue-50 to-slate-100 py-20">
            <div className="container mx-auto px-4 sm:px-6 lg:px-8">
              <div className="max-w-3xl mx-auto text-center">
                <div className="flex justify-center mb-6">
                  <Badge variant="social" className="px-4 py-2">
                    <BookOpen className="w-4 h-4 mr-2" />
                    Expert Insights
                  </Badge>
                </div>
                <h1 className="text-5xl sm:text-6xl font-bold text-slate-900 mb-6">
                  Content Protection 
                  <span className="text-blue-600 block">Knowledge Hub</span>
                </h1>
                <p className="text-xl text-slate-600 leading-relaxed">
                  Learn how to protect your content, maximize your revenue, and stay ahead 
                  of content thieves with expert insights from our team.
                </p>
              </div>
            </div>
          </section>

          {/* Featured Posts */}
          {featuredPosts.length > 0 && (
            <section className="py-16 bg-white">
              <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                <h2 className="text-3xl font-bold text-center mb-12">Featured Articles</h2>
                <div className="grid md:grid-cols-2 gap-8 max-w-6xl mx-auto">
                  {featuredPosts.map(post => (
                    <Card key={post.id} className="overflow-hidden hover:shadow-xl transition-all duration-300 group">
                      <Link to={`/blog/${post.slug}`}>
                        {post.image && (
                          <div className="aspect-video overflow-hidden">
                            <img 
                              src={post.image} 
                              alt={post.title}
                              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            />
                          </div>
                        )}
                        <CardHeader className="pb-2">
                          <div className="flex items-center gap-2 mb-3">
                            <Badge variant="secondary">{post.category}</Badge>
                            <Badge className="bg-blue-600 text-white">Featured</Badge>
                          </div>
                          <h3 className="text-xl font-bold group-hover:text-blue-600 transition-colors">
                            {post.title}
                          </h3>
                        </CardHeader>
                        <CardContent>
                          <p className="text-muted-foreground mb-4 line-clamp-3">{post.excerpt}</p>
                          <div className="flex items-center justify-between text-sm text-muted-foreground">
                            <div className="flex items-center gap-4">
                              <span className="flex items-center gap-1">
                                <User className="w-3 h-3" />
                                {post.author.name}
                              </span>
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {post.readTime} min
                              </span>
                            </div>
                            <span>{new Date(post.publishedAt).toLocaleDateString()}</span>
                          </div>
                        </CardContent>
                      </Link>
                    </Card>
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* Category Filter & All Posts */}
          <section className="py-16 bg-slate-50">
            <div className="container mx-auto px-4 sm:px-6 lg:px-8">
              <div className="max-w-6xl mx-auto">
                {/* Category Filter */}
                <div className="flex flex-wrap justify-center gap-2 mb-12">
                  {categories.map(category => (
                    <Button
                      key={category}
                      variant={selectedCategory === category ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSelectedCategory(category)}
                      className="rounded-full"
                    >
                      {category}
                    </Button>
                  ))}
                </div>

                {/* Posts Grid */}
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                  {filteredPosts.map(post => (
                    <Card key={post.id} className="hover:shadow-lg transition-shadow group">
                      <Link to={`/blog/${post.slug}`}>
                        {post.image && (
                          <div className="aspect-video overflow-hidden rounded-t-lg">
                            <img 
                              src={post.image} 
                              alt={post.title}
                              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            />
                          </div>
                        )}
                        <CardContent className="p-6">
                          <div className="flex items-center gap-2 mb-3">
                            <Badge variant="secondary" className="text-xs">{post.category}</Badge>
                          </div>
                          <h3 className="font-semibold mb-2 group-hover:text-blue-600 transition-colors line-clamp-2">
                            {post.title}
                          </h3>
                          <p className="text-muted-foreground text-sm line-clamp-3 mb-4">
                            {post.excerpt}
                          </p>
                          <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <div className="flex items-center gap-3">
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {post.readTime}m
                              </span>
                            </div>
                            <span>{new Date(post.publishedAt).toLocaleDateString()}</span>
                          </div>
                        </CardContent>
                      </Link>
                    </Card>
                  ))}
                </div>

                {/* Newsletter CTA */}
                <div className="mt-16 text-center">
                  <Card className="max-w-2xl mx-auto bg-blue-600 text-white">
                    <CardContent className="p-8">
                      <h3 className="text-2xl font-bold mb-4">Stay Protected, Stay Informed</h3>
                      <p className="mb-6 opacity-90">
                        Get weekly insights on content protection, new threats, and success stories 
                        delivered to your inbox.
                      </p>
                      <div className="flex gap-4 max-w-md mx-auto">
                        <input 
                          type="email" 
                          placeholder="Your email address"
                          className="flex-1 px-4 py-2 rounded-md text-slate-900"
                        />
                        <Button variant="secondary">Subscribe</Button>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </div>
          </section>
        </main>
      </div>
    </>
  );
};

export default BlogPage;